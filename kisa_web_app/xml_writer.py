from pathlib import Path
import xml.etree.ElementTree as ET
from config import OUTPUT_DIR

def seconds_to_time(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hh, remainder = divmod(seconds, 3600)
    mm, ss = divmod(remainder, 60)
    return f'{hh:02}:{mm:02}:{ss:02}'

def write_sa_xml(filename: str, events: list[dict[str, str]], output_dir: Path=OUTPUT_DIR) -> Path:
    events = sorted(events, key=lambda event: event['StartTime'])
    root = ET.Element('KisaLibraryIndex')
    library = ET.SubElement(root, 'Library')
    clip = ET.SubElement(library, 'Clip')
    header = ET.SubElement(clip, 'Header')
    ET.SubElement(header, 'AlarmEvents').text = str(len(events))
    ET.SubElement(header, 'Filename').text = filename
    alarms = ET.SubElement(clip, 'Alarms')
    for event in events:
        alarm = ET.SubElement(alarms, 'Alarm')
        ET.SubElement(alarm, 'StartTime').text = event['StartTime']
        ET.SubElement(alarm, 'AlarmDescription').text = event['AlarmDescription']
        ET.SubElement(alarm, 'AlarmDuration').text = event.get('AlarmDuration', '00:01:00')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'{Path(filename).stem}.xml'
    tree = ET.ElementTree(root)
    ET.indent(tree, space=' ')
    tree.write(output_path, encoding='UTF-8', xml_declaration=True)
    return output_path
