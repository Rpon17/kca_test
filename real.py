
import asyncio
import ipaddress
import re
import sys
import time
import functools
import xml.etree.ElementTree as ET

from pathlib import Path
from threading import Lock
from typing import Any


# ==========================================
# 1. 기본 경로 설정
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent

LIST_XML = PROJECT_DIR / "RTSP_streaming_list.xml"

OUTPUT_DIR = Path(r"C:\KISAresult")

SENTINEL_BACKEND = Path(
    r"C:\자동화도구\sentinelcv\backend"
)

PERSON_MODEL = PROJECT_DIR / "yolov8n.pt"

POSE_MODEL = PROJECT_DIR / "yolov8n-pose.pt"


# ==========================================
# 2. 탐지 구역 설정
# ==========================================

# 실제 시험 영상에 맞춰 구역 좌표를 지정해야 함.
# 현재는 비어 있으므로 구역 기반 침입/배회 탐지가
# 발생하지 않을 수 있음.

ZONES: list[dict[str, Any]] = []

# 예시:
#
# ZONES = [
#     {
#         "name": "intrusion_zone",
#         "points": [
#             [100, 100],
#             [500, 100],
#             [500, 400],
#             [100, 400],
#         ],
#         "type": "restricted",
#         "priority": "ALTA",
#     }
# ]


# ==========================================
# 3. 이벤트 이름 변환
# ==========================================

# 현재 제공된 KISA SA XML 샘플에서
# 확인된 이벤트 이름만 매핑함.
#
# 낙상은 KISA 표기값 확인 후 추가해야 함.

EVENT_NAME_MAP = {
    "LOITERING": "Loitering",
    "INTRUSION": "Intrusion",
    "FALL_DETECTED": None,
    "PERSON_DOWN": None,
}


# ==========================================
# 4. 영상 목록 XML 읽기
# ==========================================

def load_video_list(path: Path) -> list[str]:

    if not path.is_file():
        raise FileNotFoundError(
            f"영상 목록 XML이 없습니다: {path}"
        )

    root = ET.parse(path).getroot()

    names = []

    # KISA 안내서 형식
    for node in root.findall(
        ".//Clips/Video/Clip/FileName"
    ):
        if node.text and node.text.strip():
            names.append(
                Path(node.text.strip()).name
            )

    # 다른 목록 형식도 지원
    if not names:
        for node in root.findall(
            ".//Files/File/Name"
        ):
            if node.text and node.text.strip():
                names.append(
                    Path(node.text.strip()).name
                )

    if not names:
        raise ValueError(
            "영상 목록에서 파일명을 찾지 못했습니다."
        )

    for name in names:
        if (
            name in {".", ".."}
            or not re.fullmatch(
                r'[^<>:"/\\|?*]+\.[A-Za-z0-9]+',
                name
            )
        ):
            raise ValueError(
                f"잘못된 영상 파일명: {name}"
            )

    count_node = root.find(".//NumOfFiles")

    if (
        count_node is not None
        and count_node.text
    ):
        expected = int(count_node.text.strip())

        if expected != len(names):
            raise ValueError(
                f"영상 개수 불일치: "
                f"목록={expected}, 실제={len(names)}"
            )

    return names


# ==========================================
# 5. RTSP 주소 입력
# ==========================================

def ask_rtsp_url() -> str:

    raw = input(
        "RTSP 서버 IP 또는 주소 입력: "
    ).strip()

    if not raw:
        raise ValueError(
            "RTSP 주소를 입력해야 합니다."
        )

    if raw.lower().startswith("rtsp://"):
        return raw

    if ":" in raw:
        return f"rtsp://{raw}/"

    ipaddress.ip_address(raw)

    return f"rtsp://{raw}:8554/"


# ==========================================
# 6. 시간 변환
# ==========================================

def seconds_to_time(seconds: int) -> str:

    seconds = max(0, int(seconds))

    hh, remainder = divmod(seconds, 3600)

    mm, ss = divmod(remainder, 60)

    return f"{hh:02}:{mm:02}:{ss:02}"


# ==========================================
# 7. KISA SA XML 생성
# ==========================================

def write_sa_xml(
    filename: str,
    events: list[dict[str, str]],
    output_dir: Path = OUTPUT_DIR,
) -> Path:

    events = sorted(
        events,
        key=lambda event: event["StartTime"]
    )

    root = ET.Element("KisaLibraryIndex")

    library = ET.SubElement(
        root,
        "Library"
    )

    clip = ET.SubElement(
        library,
        "Clip"
    )

    header = ET.SubElement(
        clip,
        "Header"
    )

    ET.SubElement(
        header,
        "AlarmEvents"
    ).text = str(len(events))

    ET.SubElement(
        header,
        "Filename"
    ).text = filename

    alarms = ET.SubElement(
        clip,
        "Alarms"
    )

    for event in events:

        alarm = ET.SubElement(
            alarms,
            "Alarm"
        )

        ET.SubElement(
            alarm,
            "StartTime"
        ).text = event["StartTime"]

        ET.SubElement(
            alarm,
            "AlarmDescription"
        ).text = event["AlarmDescription"]

        ET.SubElement(
            alarm,
            "AlarmDuration"
        ).text = event.get(
            "AlarmDuration",
            "00:00:00"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        output_dir
        / f"{Path(filename).stem}.xml"
    )

    tree = ET.ElementTree(root)

    ET.indent(
        tree,
        space=" "
    )

    tree.write(
        output_path,
        encoding="UTF-8",
        xml_declaration=True
    )

    return output_path


# ==========================================
# 8. 영상별 이벤트 관리
# ==========================================

class EventCollector:

    def __init__(
        self,
        filenames: list[str]
    ):

        self.filenames = filenames

        self.index = 0

        self.video_started = time.monotonic()

        self.events = []

        self.seen = set()

        self.lock = Lock()

    @property
    def current_filename(self):

        if self.index >= len(self.filenames):
            return None

        return self.filenames[self.index]

    # SentinelCV 이벤트 콜백
    async def on_event(
        self,
        event,
        response_ms=None
    ):

        with self.lock:

            filename = self.current_filename

            if filename is None:
                return

            event_type = getattr(
                event,
                "event_type",
                ""
            )

            event_type = getattr(
                event_type,
                "value",
                event_type
            )

            event_type = str(
                event_type
            ).upper()

            description = EVENT_NAME_MAP.get(
                event_type
            )

            if description is None:

                print(
                    f"[주의] {filename}: "
                    f"{event_type} 매핑 없음"
                )

                return

            elapsed = int(
                time.monotonic()
                - self.video_started
            )

            start_time = seconds_to_time(
                elapsed
            )

            track_id = getattr(
                event,
                "track_id",
                None
            )

            dedupe_key = (
                event_type,
                track_id,
                start_time
            )

            if dedupe_key in self.seen:
                return

            self.seen.add(
                dedupe_key
            )

            self.events.append({
                "StartTime": start_time,
                "AlarmDescription": description,
                "AlarmDuration": "00:00:00",
            })

            print(
                f"[이벤트] "
                f"{filename} "
                f"{start_time} "
                f"{description}"
            )

    # 현재 영상 XML 저장
    def finish_current_video(self):

        with self.lock:

            filename = self.current_filename

            if filename is None:
                return None

            output_path = write_sa_xml(
                filename,
                list(self.events)
            )

            print(
                f"[XML 저장] {output_path}"
            )

            print(
                f"[이벤트 수] "
                f"{len(self.events)}"
            )

            self.index += 1

            self.events.clear()

            self.seen.clear()

            self.video_started = (
                time.monotonic()
            )

            return output_path


# ==========================================
# 9. 메인 RTSP 분석
# ==========================================

async def run():

    # 영상 목록
    filenames = load_video_list(
        LIST_XML
    )

    # RTSP 주소 입력
    rtsp_url = ask_rtsp_url()

    print()
    print("========== KISA CCTV ==========")

    print(
        f"영상 목록: {LIST_XML}"
    )

    print(
        f"영상 개수: {len(filenames)}"
    )

    for index, filename in enumerate(
        filenames,
        start=1
    ):
        print(
            f"{index}. {filename}"
        )

    print(
        f"RTSP 주소: {rtsp_url}"
    )

    print(
        f"XML 저장 위치: {OUTPUT_DIR}"
    )

    print("================================")
    print()

    # 경로 확인
    if not SENTINEL_BACKEND.is_dir():
        raise FileNotFoundError(
            f"SentinelCV 경로 없음: "
            f"{SENTINEL_BACKEND}"
        )

    if not PERSON_MODEL.is_file():
        raise FileNotFoundError(
            f"YOLO 모델 없음: {PERSON_MODEL}"
        )

    if not POSE_MODEL.is_file():
        raise FileNotFoundError(
            f"Pose 모델 없음: {POSE_MODEL}"
        )

    # SentinelCV import
    sys.path.insert(
        0,
        str(SENTINEL_BACKEND)
    )

    from detection.pipeline import (
        detection_manager,
        CameraDetectionPipeline,
        _RtspReader,
    )

    import torch

    device = (
        "cuda:0"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(
        f"[추론 장치] {device}"
    )

    # RTSP 상태 메시지 큐
    stream_events = asyncio.Queue()

    loop = asyncio.get_running_loop()

    # 원본 함수 백업
    original_open_capture = (
        CameraDetectionPipeline._open_capture
    )

    original_latest = (
        _RtspReader.latest
    )

    original_reader_run = (
        _RtspReader._run
    )

    # --------------------------------------
    # RTSP 연결 성공 감지
    # --------------------------------------

    @functools.wraps(
        original_open_capture
    )
    def capture_with_boundary(
        self,
        *args,
        **kwargs
    ):

        cap = original_open_capture(
            self,
            *args,
            **kwargs
        )

        if (
            cap is not None
            and getattr(
                self,
                "is_rtsp_source",
                False
            )
        ):

            loop.call_soon_threadsafe(
                stream_events.put_nowait,
                (
                    "open",
                    time.monotonic()
                )
            )

        return cap

    # --------------------------------------
    # 이전 영상의 마지막 프레임 방지
    # --------------------------------------

    def latest_without_stale_frame(
        self
    ):

        if not self._t.is_alive():
            return None

        return original_latest(
            self
        )

    # --------------------------------------
    # RTSP 프레임 읽기 종료 감지
    # --------------------------------------

    def reader_with_eof_signal(
        self
    ):

        original_reader_run(
            self
        )

        if self._running:

            loop.call_soon_threadsafe(
                stream_events.put_nowait,
                (
                    "eof",
                    time.monotonic()
                )
            )

    # 함수 연결
    CameraDetectionPipeline._open_capture = (
        capture_with_boundary
    )

    _RtspReader.latest = (
        latest_without_stale_frame
    )

    _RtspReader._run = (
        reader_with_eof_signal
    )

    collector = EventCollector(
        filenames
    )

    # SentinelCV 이벤트 루프 등록
    detection_manager.set_loop(
        loop
    )

    # --------------------------------------
    # 탐지 설정
    # --------------------------------------

    config = {
        "loitering_detection": True,
        "loitering_threshold": 10,
        "intrusion_enabled": True,
        "fall_detection": True,
        "person_down_seconds": 20,
        "pose_infer_every": 1,
    }

    try:

        # 기존 SentinelCV 탐지 파이프라인
        detection_manager.add_camera(
            camera_id="kisa-test-camera",
            camera_name="KISA RTSP Test",
            source=rtsp_url,
            zones=ZONES,
            config=config,
            on_event_callback=collector.on_event,
            on_invalid_frame_callback=None,
            model_path=str(PERSON_MODEL),
            pose_model_path=str(POSE_MODEL),
            device=device,
            confidence=0.35,
            frame_skip=1,
        )

        print()
        print("[분석 시작]")
        print("RTSP 연결 대기 중...")
        print()

        clip_active = False

        connection_count = 0

        # ----------------------------------
        # 영상 순차 처리
        # ----------------------------------

        while collector.current_filename is not None:

            try:

                kind, occurred_at = (
                    await asyncio.wait_for(
                        stream_events.get(),
                        timeout=1.0
                    )
                )

            except asyncio.TimeoutError:
                continue

            # RTSP 연결 성공
            if kind == "open":

                connection_count += 1

                if not clip_active:

                    with collector.lock:

                        collector.video_started = (
                            occurred_at
                        )

                    clip_active = True

                    print(
                        f"[영상 시작] "
                        f"{collector.current_filename}"
                    )

                    print(
                        f"[RTSP 연결] "
                        f"{connection_count}회"
                    )

                else:

                    print(
                        "[주의] EOF 신호 없이 "
                        "RTSP가 다시 연결됨"
                    )

            # RTSP 송출 종료
            elif (
                kind == "eof"
                and clip_active
            ):

                print()
                print(
                    "[RTSP 종료 감지]"
                )

                print(
                    f"[영상 종료] "
                    f"{collector.current_filename}"
                )

                # 이미 예약된 탐지 콜백 처리 대기
                await asyncio.sleep(
                    0.5
                )

                # XML 저장
                collector.finish_current_video()

                clip_active = False

                # 마지막 영상 확인
                if collector.current_filename is None:

                    print()
                    print(
                        "[전체 영상 처리 완료]"
                    )

                    break

                print()
                print(
                    "[다음 영상 대기] "
                    f"{collector.current_filename}"
                )

    except asyncio.CancelledError:

        print(
            "[중단] 실행이 취소되었습니다."
        )

    finally:

        detection_manager.stop_all()

        # 원본 함수 복구
        CameraDetectionPipeline._open_capture = (
            original_open_capture
        )

        _RtspReader.latest = (
            original_latest
        )

        _RtspReader._run = (
            original_reader_run
        )

        if collector.current_filename is not None:

            print(
                "[주의] 미완료 영상: "
                f"{collector.current_filename}"
            )


# ==========================================
# 10. 프로그램 시작
# ==========================================

if __name__ == "__main__":

    try:

        asyncio.run(
            run()
        )

    except KeyboardInterrupt:

        print(
            "\n[사용자 종료]"
        )

    except Exception as exc:

        print(
            f"\n[오류] {exc}"
        )

        raise
