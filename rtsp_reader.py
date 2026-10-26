import os
import cv2
import time


def open_rtsp(rtsp_url: str):
    """
    RTSP 스트림에 연결한다.
    연결 실패 시 None을 반환한다.
    """
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"

    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        cap.release()
        print("RTSP 연결 실패: 주소와 서버 상태를 확인하세요.")
        return None

    print("RTSP 연결 성공")
    return cap


def read_rtsp(rtsp_url: str):
    cap = open_rtsp(rtsp_url)

    if cap is None:
        return

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("프레임 수신 실패 또는 스트림 종료")
                break

            cv2.imshow("KISA RTSP Viewer", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    rtsp_url = input("RTSP 주소를 입력하세요: ").strip()

    if rtsp_url:
        read_rtsp(rtsp_url)
    else:
        print("RTSP 주소가 입력되지 않았습니다.")