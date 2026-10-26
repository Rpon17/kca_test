
import os
import cv2
import time
from ultralytics import YOLO

# RTSP 서버의 실제 영상 주소
RTSP_URL = "rtsp://192.168.0.42:8554/"

# YOLO 모델 설정
MODEL_PATH = "yolov8n.pt"
CONFIDENCE = 0.4

# RTSP 연결 시간 제한(ms)
OPEN_TIMEOUT_MS = 15000
READ_TIMEOUT_MS = 15000


def open_rtsp(rtsp_url: str):
    """
    UDP로 RTSP 연결을 시도한다.
    실패하면 TCP로 재시도한다.
    """
    for transport in ("udp", "tcp"):
        print(f"RTSP 연결 시도: {transport.upper()}")

        # OpenCV FFmpeg 전송 방식 설정
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            f"rtsp_transport;{transport}"
        )

        cap = cv2.VideoCapture()

        # 연결 및 프레임 수신 시간 제한 설정
        params = [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
            OPEN_TIMEOUT_MS,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC,
            READ_TIMEOUT_MS,
        ]

        opened = cap.open(
            rtsp_url,
            cv2.CAP_FFMPEG,
            params
        )

        if opened and cap.isOpened():
            print(f"RTSP 연결 성공: {transport.upper()}")
            return cap

        print(f"{transport.upper()} 연결 실패")
        cap.release()
        time.sleep(1)

    print("RTSP 연결에 실패했습니다.")
    print("주소, Video load 상태, 서버의 전송 방식 지원 여부를 확인하세요.")
    return None


def main():
    # 1. YOLO 모델 로드
    print("YOLO 모델을 불러오는 중...")
    model = YOLO(MODEL_PATH)
    print("YOLO 모델 로드 완료")

    # 2. RTSP 영상 연결
    cap = open_rtsp(RTSP_URL)

    if cap is None:
        return

    print("사람 탐지를 시작합니다.")
    print("종료하려면 ESC 키를 누르세요.")

    frame_count = 0

    try:
        while True:
            # 3. RTSP 프레임 수신
            ret, frame = cap.read()

            if not ret or frame is None:
                print("영상 프레임 수신 실패")
                break

            frame_count += 1

            # 4. YOLO로 사람 탐지
            results = model.predict(
                source=frame,
                classes=[0],  # COCO 클래스 0 = person
                conf=CONFIDENCE,
                verbose=False
            )

            # 5. 탐지 결과를 영상에 표시
            annotated_frame = results[0].plot()

            # 현재 프레임에서 탐지된 사람 수 표시
            person_count = len(results[0].boxes)

            cv2.putText(
                annotated_frame,
                f"People: {person_count}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            cv2.imshow(
                "KISA - YOLO Person Detection",
                annotated_frame
            )

            # 100프레임마다 진행 상황 출력
            if frame_count % 100 == 0:
                print(
                    f"수신 프레임: {frame_count}, "
                    f"현재 탐지 인원: {person_count}"
                )

            # ESC 키를 누르면 종료
            if cv2.waitKey(1) & 0xFF == 27:
                break

    except KeyboardInterrupt:
        print("사용자가 프로그램을 종료했습니다.")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("RTSP 연결 종료")


if __name__ == "__main__":
    main()
