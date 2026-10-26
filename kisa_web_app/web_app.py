"""Local-only KISA operator interface. Start with: python web_app.py"""
from __future__ import annotations
import html
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import webbrowser
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

from config import LIST_XML, OUTPUT_DIR
from video_list import load_video_list

BASE = Path(__file__).resolve().parent
app = FastAPI(title='KISA CCTV local control')
_lock = threading.RLock()
_proc = None
_lines: list[str] = []

class Paste(BaseModel):
    raw: str
class Start(BaseModel):
    url: str

def parse_names(raw: str) -> list[str]:
    # A developer-tools copy contains escaped angle brackets and literal \\r\\n.
    raw = raw.replace('\\<', '<').replace('\\>', '>')
    names = re.findall(r'<Name>\s*([^<>]*?\.mp4)\s*</Name>', raw, re.I)
    if not names:
        raise ValueError('w_value의 <Name>파일명.mp4</Name> 항목을 찾지 못했습니다.')
    if len(names) > 10000:
        raise ValueError('영상 목록이 너무 깁니다.')
    for name in names:
        if name != name.strip() or '/' in name or '\\' in name or not re.fullmatch(r'[\w .()\-]+\.mp4', name, re.I):
            raise ValueError(f'허용되지 않는 영상 파일명: {name!r}')
    return names

def normalize_rtsp(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise ValueError('RTSP 주소를 입력하세요.')
    if '://' not in raw:
        raw = 'rtsp://' + raw
    parts = urlsplit(raw)
    if parts.scheme != 'rtsp' or not parts.hostname or parts.username or parts.password:
        raise ValueError('rtsp://IP:포트/ 형태의 주소를 입력하세요.')
    if parts.port is None:
        host = parts.hostname
        if ':' in host: host = f'[{host}]'
        raw = f'rtsp://{host}:8554{parts.path or "/"}'
    return raw

def collect_output(process):
    try:
        for line in process.stdout:
            with _lock:
                _lines.append(line.rstrip())
                if len(_lines) > 2000:
                    del _lines[:500]
    finally:
        with _lock:
            _lines.append(f'[프로세스 종료] 종료 코드: {process.wait()}')

@app.get('/', response_class=HTMLResponse)
def index():
    return HTML

@app.get('/api/status')
def status():
    with _lock:
        running = _proc is not None and _proc.poll() is None
        try: names = load_video_list(LIST_XML)
        except (OSError, ValueError, ET.ParseError): names = []
        files = []
        if OUTPUT_DIR.is_dir():
            files = [{'name':p.name,'size':p.stat().st_size} for p in sorted(OUTPUT_DIR.glob('*.xml')) if p.is_file()]
        return {'running':running,'names':names,'files':files,'logs':_lines[-300:]}

@app.post('/api/list')
def make_list(data: Paste):
    with _lock:
        if _proc is not None and _proc.poll() is None:
            raise HTTPException(409, '분석 중에는 영상 목록을 변경할 수 없습니다.')
        try: names = parse_names(data.raw)
        except ValueError as e: raise HTTPException(400, str(e))
        root = ET.Element('StreamingFileList')
        ET.SubElement(root,'ListFormatVersion').text = '1.0'
        ET.SubElement(root,'NumOfFiles').text = str(len(names))
        files = ET.SubElement(root,'Files')
        for name in names:
            ET.SubElement(ET.SubElement(files,'File'),'Name').text = name
        ET.indent(root, space='    ')
        ET.ElementTree(root).write(LIST_XML,encoding='UTF-8',xml_declaration=True)
        return {'names':names}

@app.post('/api/start')
def start(data: Start):
    global _proc
    with _lock:
        if _proc is not None and _proc.poll() is None:
            raise HTTPException(409,'이미 분석 중입니다.')
        try:
            load_video_list(LIST_XML)
            url = normalize_rtsp(data.url)
        except (ValueError,OSError,ET.ParseError) as e:
            raise HTTPException(400,str(e))
        _lines.clear()
        # The existing analysis program reads its RTSP address from stdin.
        _proc = subprocess.Popen([sys.executable,'-u',str(BASE/'pipeline.py')],cwd=BASE,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding='utf-8',errors='replace',bufsize=1)
        _proc.stdin.write(url+'\n')
        _proc.stdin.flush()
        _proc.stdin.close()
        threading.Thread(target=collect_output,args=(_proc,),daemon=True).start()
        return {'ok':True}

@app.post('/api/stop')
def stop():
    with _lock:
        if _proc is None or _proc.poll() is not None:
            return {'ok':True}
        _proc.terminate()
        _lines.append('[사용자 요청] 분석 프로세스 종료. 진행 중인 영상의 XML은 저장되지 않을 수 있습니다.')
        return {'ok':True}

@app.get('/api/result/{name}')
def result(name: str):
    if not re.fullmatch(r'[\w.()\-]+\.xml',name,re.I) or Path(name).name != name:
        raise HTTPException(400,'잘못된 파일명')
    path = OUTPUT_DIR/name
    if not path.is_file(): raise HTTPException(404,'파일이 없습니다.')
    return FileResponse(path,media_type='application/xml',filename=name)

HTML = r'''<!doctype html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KISA CCTV 분석 관리</title>
<style>*{box-sizing:border-box}body{font-family:system-ui,'Malgun Gothic',sans-serif;background:#f4f6fa;color:#192436;margin:0}main{max-width:940px;margin:35px auto;padding:0 20px}h1{font-size:26px;margin-bottom:6px}p{color:#5b6676}section{background:white;border:1px solid #e2e7f0;border-radius:14px;padding:24px;margin:20px 0;box-shadow:0 3px 14px #152b4910}h2{font-size:19px;margin-top:0}textarea,input{width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:8px;font:inherit}textarea{min-height:150px;font-family:Consolas,monospace;font-size:13px}button{border:0;background:#2059d5;color:white;border-radius:8px;padding:11px 17px;font-weight:700;cursor:pointer}button:disabled{opacity:.45;cursor:default}button.secondary{background:#e8edf5;color:#23324c}button.danger{background:#c73e48}.row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:12px}.pill{border-radius:20px;padding:6px 12px;background:#e7edf6;font-size:13px}pre{background:#111b2a;color:#c5e5c9;padding:16px;border-radius:9px;height:250px;overflow:auto;white-space:pre-wrap;font-size:12px}ul{line-height:1.9}a{color:#2059d5}small{color:#65758b}.msg{margin-top:10px;min-height:20px;color:#2059d5}</style></head><body><main><h1>KISA CCTV RTSP 분석 관리</h1><p>이 화면은 현재 PC에서만 사용하는 로컬 관리 페이지입니다. 영상 목록 생성 → 분석 시작 → 결과 확인 순서로 진행하세요.</p>
<section><h2>1. 영상 리스트 준비</h2><p>Streaming Server에서 <b>Get Video List</b>를 실행하세요. 다운로드 오류가 있으면 F12 → Sources → Scope의 <b>w_value</b> 문자열을 복사하여 아래에 붙여넣으세요.</p><textarea id="paste" placeholder='w_value: "\<?xml ... \<Name>C00_247_0001.mp4\</Name> ..."'></textarea><div class="row"><button id="make" onclick="makeList()">영상 목록 XML 생성</button><span>생성 파일: <b>RTSP_streaming_list.xml</b></span></div><div class="msg" id="listmsg"></div><div id="names"></div></section>
<section><h2>2. RTSP 분석 실행</h2><p>시험기관이 스트리밍을 시작하기 <b>직전에</b> 분석을 시작하세요.</p><label for="rtsp">KISA에서 제공한 RTSP 주소</label><input id="rtsp" placeholder="rtsp://192.168.0.42:8554/" value="rtsp://192.168.0.42:8554/"><div class="row"><button id="start" onclick="start()">▶ 분석 시작</button><button class="danger" id="stop" onclick="stop()">■ 분석 중단</button><span class="pill" id="state">상태 확인 중</span></div><p><small>분석 중단 시 현재 영상의 XML은 생성되지 않을 수 있습니다.</small></p><h3>실시간 분석 로그</h3><pre id="logs">로그 대기 중...</pre></section>
<section><h2>3. 결과 XML 확인</h2><p>결과 저장 위치: <b>C:\KISAresult</b></p><div class="row"><button class="secondary" onclick="refresh()">새로고침</button><button class="secondary" onclick="copyPath()">결과 폴더 경로 복사</button></div><div id="files"><p>결과를 불러오는 중...</p></div><small>파일명 링크를 클릭하면 XML을 다운로드합니다. 분석 종료 후 파일 수와 영상 목록 수가 일치하는지 확인하세요.</small></section></main>
<script>
const $=id=>document.getElementById(id);
async function api(url,opts){const r=await fetch(url,opts);const v=await r.json();if(!r.ok)throw Error(v.detail||'요청 실패');return v}
function post(url,data){return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function makeList(){try{const d=await post('/api/list',{raw:$('paste').value});$('listmsg').textContent=`생성 완료: ${d.names.length}개 영상`;refresh()}catch(e){$('listmsg').textContent='오류: '+e.message}}
async function start(){try{await post('/api/start',{url:$('rtsp').value});refresh()}catch(e){alert(e.message)}}
async function stop(){if(!confirm('분석을 중단할까요? 현재 영상 XML이 누락될 수 있습니다.'))return;try{await post('/api/stop',{});refresh()}catch(e){alert(e.message)}}
function copyPath(){navigator.clipboard.writeText('C:\\KISAresult').then(()=>alert('경로 복사 완료')).catch(()=>alert('C:\\KISAresult'))}
async function refresh(){try{const d=await api('/api/status');$('state').textContent=d.running?'● 분석 중':'○ 대기 / 종료';$('start').disabled=d.running;$('stop').disabled=!d.running;$('make').disabled=d.running;$('names').innerHTML=d.names.length?'<b>현재 영상 목록 ('+d.names.length+'개)</b><ol>'+d.names.map(n=>'<li>'+escapeHtml(n)+'</li>').join('')+'</ol>':'<p>생성된 영상 목록이 없습니다.</p>';$('files').innerHTML=d.files.length?'<ul>'+d.files.map(f=>'<li><a href="/api/result/'+encodeURIComponent(f.name)+'">'+escapeHtml(f.name)+'</a> ('+f.size+' bytes)</li>').join('')+'</ul>':'<p>아직 생성된 XML 파일이 없습니다.</p>';$('logs').textContent=d.logs.join('\n')||'로그 대기 중...';$('logs').scrollTop=$('logs').scrollHeight}catch(e){$('state').textContent='연결 오류'}}
refresh();setInterval(refresh,1500);
</script></body></html>'''

if __name__ == '__main__':
    print('KISA 웹 관리 페이지: http://127.0.0.1:8765')
    webbrowser.open('http://127.0.0.1:8765')
    uvicorn.run(app,host='127.0.0.1',port=8765,log_level='warning')
