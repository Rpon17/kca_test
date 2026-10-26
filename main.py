from pathlib import Path
import cv2

from config import VIDEO_SOURCE


def main():
    video_path = Path(VIDEO_SOURCE)

    if not video_path.exists():
        print(f"영상 파일을 찾을 수 없습니다: {video_path}")
        print("테스트 영상을 videos 폴더에 넣고 이름을 test.mp4로 지정하세요.")
        return

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print("영상을 열 수 없습니다.")
        return

    print("영상 열기 성공. ESC 키를 누르면 종료합니다.")

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        cv2.imshow("KISA CCTV Test", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
