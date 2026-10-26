# KISA CCTV RTSP 분석 프로그램

KCA 지능형 CCTV 사전시험을 위한 RTSP 영상 분석 프로그램입니다.

KCA에서 제공하는 RTSP 영상 스트림을 수신하여 AI 모델로 분석하고, 영상별 CA XML 결과 파일을 생성합니다.

## 1. 프로그램 실행

PowerShell에서 다음 명령어를 순서대로 실행합니다.

```powershell
cd C:\kisa_cctv
.\.venv311\Scripts\Activate.ps1
python web_app.py
```

실행 후 웹 브라우저에서 아래 주소로 접속합니다.

**http://127.0.0.1:8765**

## 2. 영상 목록 준비

1. KCA에서 제공하는 Streaming Server 웹페이지에 접속합니다.
2. `Get Video List`를 클릭하여 영상 목록을 요청합니다.
3. 영상 목록을 정상적으로 가져오지 못하는 경우 `F12`를 눌러 개발자 도구를 엽니다.
4. `Sources` 탭에서 영상 목록을 처리하는 코드 위치(약 68번째 줄)에 중단점을 설정합니다.
5. `Get Video List`를 다시 클릭하여 실행을 일시 정지합니다.
6. 우측 `Scope`에서 `w_value` 값을 복사합니다.
7. 제작한 웹페이지의 **영상 목록 생성** 영역에 복사한 값을 붙여넣습니다.
8. **목록 XML 생성** 버튼을 클릭합니다.

생성이 완료되면 다음 경로에 영상 목록 파일이 저장됩니다.

`C:\kisa_cctv\RTSP_streaming_list.xml`

## 3. RTSP 영상 분석

1. 제작한 웹페이지의 **RTSP 분석** 영역에 KCA에서 제공한 RTSP 주소를 입력합니다.
2. KCA에서 영상 송출을 시작하기 직전에 **분석 시작** 버튼을 클릭합니다.
3. KCA Streaming Server에서 `Upload Video`를 클릭하여 RTSP 영상 송출을 시작합니다.
4. 프로그램이 RTSP 영상을 수신하여 AI 분석을 진행합니다.
5. 분석 진행 상황은 웹페이지의 **분석 로그** 영역에서 확인할 수 있습니다.

웹페이지는 기존 `pipeline.py`를 실행하며, 영상 목록을 기준으로 각 영상의 분석 결과를 처리합니다.

## 4. CA XML 결과 확인

영상별 분석이 완료되면 CA XML 파일이 다음 경로에 저장됩니다.

`C:\KISAresult`

예시:

```text
C:\KISAresult\
├── C00_247_0001.xml
├── C00_247_0002.xml
└── C00_239_0001.xml
```

생성된 CA XML 파일의 기본 구조는 KCA에서 제공한 예시 형식에 맞춰 구현하였습니다.

분석이 완료되면 결과 파일을 확인한 후 KCA 측에 제출합니다.

## 5. 콘솔에서 직접 실행하는 방법

웹페이지를 사용하지 않고 개별 프로그램을 직접 실행할 수도 있습니다.

### 영상 목록 생성

```powershell
cd C:\kisa_cctv
.\.venv311\Scripts\Activate.ps1
python list_maker.py
```

`w_value` 문자열을 붙여넣은 후 새 줄에 `q`를 입력하면 영상 목록 XML이 생성됩니다.

### RTSP 분석

```powershell
cd C:\kisa_cctv
.\.venv311\Scripts\Activate.ps1
python pipeline.py
```

프로그램에서 RTSP 주소를 요청하면 KCA에서 제공한 주소를 입력합니다.

분석 결과는 `C:\KISAresult` 폴더에서 확인할 수 있습니다.

## 6. 참고 사항

- AI 분석에는 외부에서 확보한 YOLO 모델을 사용합니다.
- 모델의 실제 탐지 정확도는 별도로 검증하지 않았습니다.
- 이벤트 지속시간은 현재 1분으로 설정되어 있습니다.
- CA XML 파일의 기본 구조는 KCA 제공 예시와 일치하지만, 실제 시험 적합성은 추가 검증이 필요합니다.
- 영상별 결과 파일 생성 시점은 RTSP 영상 종료 감지 및 분석 처리 상태에 따라 달라질 수 있습니다.