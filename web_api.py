
import os
import subprocess
import sys
import threading
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, PlainTextResponse
import uvicorn

BASE = Path(__file__).resolve().parent
app = FastAPI()

logs = []
process = None
process_lock = threading.Lock()


def run_pipeline(rtsp_url):
    global process

    try:
        with process_lock:
            process = subprocess.Popen(
                [sys.executable, "-u", str(BASE / "pipeline.py")],
                cwd=BASE,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={
                    **os.environ,
                    "PYTHONIOENCODING": "utf-8",
                },
            )

            current_process = process

        current_process.stdin.write(rtsp_url + "\n")
        current_process.stdin.flush()
        current_process.stdin.close()

        for line in current_process.stdout:
            logs.append(line.rstrip())

            if len(logs) > 500:
                del logs[:-500]

        current_process.wait()
        logs.append(f"[종료 코드] {current_process.returncode}")

    except Exception as exc:
        logs.append(f"[실행 오류] {exc}")


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <title>KISA CCTV 테스트</title>
    </head>

    <body style="font-family:Arial;max-width:800px;margin:40px auto">

        <h2>KISA CCTV 테스트</h2>

        <h3>1. 영상 목록 생성</h3>

        <textarea
            id="raw"
            rows="8"
            style="width:100%"
            placeholder="w_value 붙여넣기"
        ></textarea>

        <br><br>

        <button type="button" onclick="makeList()">
            목록 XML 생성
        </button>

        <h3>2. RTSP 분석</h3>

        <input
            id="rtsp"
            style="width:70%"
            value="rtsp://192.168.0.42:8554/"
        >

        <button type="button" onclick="startAnalysis()">
            분석 시작
        </button>

        <br><br>

        <button type="button" onclick="stopAnalysis()">
            분석 중단
        </button>

        <h3>3. 분석 로그</h3>

        <pre
            id="log"
            style="background:#eee;padding:15px;height:300px;overflow:auto"
        ></pre>

        <p>결과 XML 저장 위치: C:\\KISAresult</p>

        <script>

        // 영상 목록 XML 생성
        async function makeList() {
            const raw = document.getElementById("raw").value;

            if (!raw.trim()) {
                alert("w_value를 입력하세요.");
                return;
            }

            const form = new FormData();
            form.append("raw", raw);

            try {
                const response = await fetch("/list", {
                    method: "POST",
                    body: form
                });

                const result = await response.json();

                if (result.success) {
                    alert("생성 완료!");
                } else {
                    alert("생성 실패: " + result.message);
                }

            } catch (error) {
                alert("오류: " + error.message);
            }
        }


        // RTSP 분석 시작
        async function startAnalysis() {
            const url = document.getElementById("rtsp").value;

            if (!url.trim()) {
                alert("RTSP 주소를 입력하세요.");
                return;
            }

            const form = new FormData();
            form.append("url", url);

            try {
                const response = await fetch("/start", {
                    method: "POST",
                    body: form
                });

                const result = await response.json();
                alert(result.message);

            } catch (error) {
                alert("오류: " + error.message);
            }
        }


        // RTSP 분석 중단
        async function stopAnalysis() {
            try {
                const response = await fetch("/stop", {
                    method: "POST"
                });

                const result = await response.json();
                alert(result.message);

            } catch (error) {
                alert("오류: " + error.message);
            }
        }


        // 실시간 분석 로그
        async function updateLogs() {
            try {
                const response = await fetch("/logs");
                const text = await response.text();

                const logBox = document.getElementById("log");
                logBox.textContent = text;
                logBox.scrollTop = logBox.scrollHeight;

            } catch (error) {
                console.error(error);
            }
        }

        setInterval(updateLogs, 1000);
        updateLogs();

        </script>

    </body>
    </html>
    """


@app.post("/list")
def make_list(raw: str = Form(...)):
    # 기존 list_maker.py를 실행하여 XML 생성
    result = subprocess.run(
        [sys.executable, str(BASE / "list_maker.py")],
        input=raw + "\nq\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=BASE,
        env={
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
        },
    )

    return {
        "success": result.returncode == 0,
        "message": result.stdout + result.stderr,
    }


@app.post("/start")
def start(url: str = Form(...)):
    global logs

    with process_lock:
        if process is not None and process.poll() is None:
            return {"message": "이미 분석 중입니다."}

        logs = []

        threading.Thread(
            target=run_pipeline,
            args=(url,),
            daemon=True,
        ).start()

    return {"message": "분석을 시작했습니다."}


@app.post("/stop")
def stop():
    with process_lock:
        if process is not None and process.poll() is None:
            process.terminate()
            return {"message": "분석 중단 요청 완료"}

    return {"message": "실행 중인 분석이 없습니다."}


@app.get("/logs", response_class=PlainTextResponse)
def get_logs():
    return "\n".join(logs[-300:])


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8765,
    )
