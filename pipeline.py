"""KISA CCTV test entry point. Run: python pipeline.py"""
import asyncio
import sys
from config import LIST_XML, OUTPUT_DIR, SENTINEL_BACKEND, PERSON_MODEL, POSE_MODEL, ZONES, DETECTION_CONFIG
from video_list import load_video_list, ask_rtsp_url
from event_collector import EventCollector
from rtsp_hooks import RtspBoundaryHooks

async def run():
    filenames = load_video_list(LIST_XML)
    rtsp_url = ask_rtsp_url()
    print()
    print('========== KISA CCTV ==========')
    print(f'영상 목록: {LIST_XML}')
    print(f'영상 개수: {len(filenames)}')
    for index, filename in enumerate(filenames, start=1):
        print(f'{index}. {filename}')
    print(f'RTSP 주소: {rtsp_url}')
    print(f'XML 저장 위치: {OUTPUT_DIR}')
    print('================================')
    print()
    if not SENTINEL_BACKEND.is_dir():
        raise FileNotFoundError(f'SentinelCV 경로 없음: {SENTINEL_BACKEND}')
    if not PERSON_MODEL.is_file():
        raise FileNotFoundError(f'YOLO 모델 없음: {PERSON_MODEL}')
    if not POSE_MODEL.is_file():
        raise FileNotFoundError(f'Pose 모델 없음: {POSE_MODEL}')
    sys.path.insert(0, str(SENTINEL_BACKEND))
    from detection.pipeline import detection_manager, CameraDetectionPipeline, _RtspReader
    import torch
    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    print(f'[추론 장치] {device}')
    stream_events = asyncio.Queue()
    loop = asyncio.get_running_loop()
    hooks = RtspBoundaryHooks(CameraDetectionPipeline, _RtspReader, loop, stream_events)
    hooks.install()
    collector = EventCollector(filenames)
    detection_manager.set_loop(loop)
    config = DETECTION_CONFIG
    try:
        detection_manager.add_camera(camera_id='kisa-test-camera', camera_name='KISA RTSP Test', source=rtsp_url, zones=ZONES, config=config, on_event_callback=collector.on_event, on_invalid_frame_callback=None, model_path=str(PERSON_MODEL), pose_model_path=str(POSE_MODEL), device=device, confidence=0.35, frame_skip=1)
        print()
        print('[분석 시작]')
        print('RTSP 연결 대기 중...')
        print()
        clip_active = False
        connection_count = 0
        while collector.current_filename is not None:
            try:
                kind, occurred_at = await asyncio.wait_for(stream_events.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            if kind == 'open':
                connection_count += 1
                if not clip_active:
                    with collector.lock:
                        collector.video_started = occurred_at
                    clip_active = True
                    print(f'[영상 시작] {collector.current_filename}')
                    print(f'[RTSP 연결] {connection_count}회')
                else:
                    print('[주의] EOF 신호 없이 RTSP가 다시 연결됨')
            elif kind == 'eof' and clip_active:
                print()
                print('[RTSP 종료 감지]')
                print(f'[영상 종료] {collector.current_filename}')
                await asyncio.sleep(0.5)
                collector.finish_current_video()
                clip_active = False
                if collector.current_filename is None:
                    print()
                    print('[전체 영상 처리 완료]')
                    break
                print()
                print(f'[다음 영상 대기] {collector.current_filename}')
    except asyncio.CancelledError:
        print('[중단] 실행이 취소되었습니다.')
    finally:
        detection_manager.stop_all()
        hooks.restore()
        if collector.current_filename is not None:
            print(f'[주의] 미완료 영상: {collector.current_filename}')
if __name__ == '__main__':
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print('\n[사용자 종료]')
    except Exception as exc:
        print(f'\n[오류] {exc}')
        raise
