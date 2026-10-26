"""KISA test paths, event mapping and detector configuration."""
from pathlib import Path
from typing import Any
PROJECT_DIR = Path(__file__).resolve().parent
LIST_XML = PROJECT_DIR / 'RTSP_streaming_list.xml'
OUTPUT_DIR = Path('C:\\KISAresult')
SENTINEL_BACKEND = Path('C:\\자동화도구\\sentinelcv\\backend')
PERSON_MODEL = PROJECT_DIR / 'yolov8n.pt'
POSE_MODEL = PROJECT_DIR / 'yolov8n-pose.pt'
ZONES: list[dict[str, Any]] = []
EVENT_NAME_MAP = {'LOITERING': 'Loitering', 'INTRUSION': 'Intrusion', 'FALL_DETECTED': None, 'PERSON_DOWN': None}
DETECTION_CONFIG = {'loitering_detection': True, 'loitering_threshold': 10, 'intrusion_enabled': True, 'fall_detection': True, 'person_down_seconds': 20, 'pose_infer_every': 1}
