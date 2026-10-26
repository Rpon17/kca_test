
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET


def create_sa_xml(filename, events, output_dir="output"):
    events = sorted(
        events,
        key=lambda e: datetime.strptime(e["start_time"], "%H:%M:%S")
    )

    root = ET.Element("KisaLibraryIndex")
    library = ET.SubElement(root, "Library")
    clip = ET.SubElement(library, "Clip")

    header = ET.SubElement(clip, "Header")
    ET.SubElement(header, "AlarmEvents").text = str(len(events))
    ET.SubElement(header, "Filename").text = filename

    alarms = ET.SubElement(clip, "Alarms")

    for event in events:
        alarm = ET.SubElement(alarms, "Alarm")
        ET.SubElement(alarm, "StartTime").text = event["start_time"]
        ET.SubElement(alarm, "AlarmDescription").text = event["description"]
        ET.SubElement(alarm, "AlarmDuration").text = event["duration"]

    tree = ET.ElementTree(root)
    ET.indent(tree, space=" ")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    xml_path = out_dir / (Path(filename).stem + ".xml")
    tree.write(xml_path, encoding="UTF-8", xml_declaration=True)

    return xml_path


if __name__ == "__main__":
    events = [
        {
            "start_time": "00:04:00",
            "description": "Intrusion",
            "duration": "00:01:00",
        },
        {
            "start_time": "00:03:00",
            "description": "Loitering",
            "duration": "00:01:00",
        },
    ]

    result = create_sa_xml("C00_001_0030.mp4", events)
    print(f"SA XML 생성 완료: {result.resolve()}")
