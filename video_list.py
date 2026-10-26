from pathlib import Path
import re
import ipaddress
import xml.etree.ElementTree as ET

def load_video_list(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f'영상 목록 XML이 없습니다: {path}')
    root = ET.parse(path).getroot()
    names = []
    for node in root.findall('.//Clips/Video/Clip/FileName'):
        if node.text and node.text.strip():
            names.append(Path(node.text.strip()).name)
    if not names:
        for node in root.findall('.//Files/File/Name'):
            if node.text and node.text.strip():
                names.append(Path(node.text.strip()).name)
    if not names:
        raise ValueError('영상 목록에서 파일명을 찾지 못했습니다.')
    for name in names:
        if name in {'.', '..'} or not re.fullmatch('[^<>:"/\\\\|?*]+\\.[A-Za-z0-9]+', name):
            raise ValueError(f'잘못된 영상 파일명: {name}')
    count_node = root.find('.//NumOfFiles')
    if count_node is not None and count_node.text:
        expected = int(count_node.text.strip())
        if expected != len(names):
            raise ValueError(f'영상 개수 불일치: 목록={expected}, 실제={len(names)}')
    return names

def ask_rtsp_url() -> str:
    raw = input('RTSP 서버 IP 또는 주소 입력: ').strip()
    if not raw:
        raise ValueError('RTSP 주소를 입력해야 합니다.')
    if raw.lower().startswith('rtsp://'):
        return raw
    if ':' in raw:
        return f'rtsp://{raw}/'
    ipaddress.ip_address(raw)
    return f'rtsp://{raw}:8554/'
