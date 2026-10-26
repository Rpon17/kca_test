# KISA CCTV RTSP 분석

###1. 영상 리스트 준비
    1. KCA에서 제공하는 Streaming Server 웹페이지에 접속한다.
    2. GET Video List를 실행하여 영상 목록을 요청한다.
    3. 영상 목록을 정상적으로 가져오지 못하는 경우 개발자 도구를 연다(F12).
    4. Sources에서 기존에 확인한 코드 위치(약 68번째 줄)에 중단점을 설정한다.
    5. 다시 GET Video List를 실행하여 중단점에서 실행을 일시 정지한다.
    6. 우측 Scope에서 w_value 값을 복사한다.
    7. list_maker.py를 실행하고 복사한 문자열을 붙여넣는다.
    8. 새 줄에 q를 입력하여 RTSP_streaming_list.xml을 생성한다.


###2. RTSP 분석 실행
    1.KCA가 스트리밍을 시작하기 직전에 PowerShell에서 분석 프로그램을 실행한다.

    cd C:\kisa_cctv
    .\.venv311\Scripts\Activate.ps1
    python pipeline.py

    2. 이후 프로그램에서 RTSP 주소를 요청하면 KCA에서 제공한 주소를 입력한다.

    3. C:\KISAresult\에서 제작된 CA XML파일을 확인하고 kca에 제공한다.


http://127.0.0.1:8765