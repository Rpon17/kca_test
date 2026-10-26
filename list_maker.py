
"""w_value 문자열에서 영상 파일명을 추출해 RTSP_streaming_list.xml 생성"""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

OUTPUT = Path(__file__).resolve().parent / "RTSP_streaming_list.xml"


def extract_names(raw: str) -> list[str]:
    # 개발자 도구에서 복사한 \<Name> 형태도 처리
    text = raw.replace("\\<", "<").replace("\\>", ">")

    names = re.findall(
        r"<Name>\s*([^<>]*?\.mp4)\s*</Name>",
        text,
        flags=re.IGNORECASE,
    )

    if not names:
        raise ValueError(
            "w_value에서 <Name>...mp4</Name> 항목을 찾지 못했습니다."
        )

    # 입력된 순서와 중복 파일명 유지
    for name in names:
        if "/" in name or "\\" in name or name.strip() != name:
            raise ValueError(f"잘못된 영상 파일명: {name!r}")

    return names


def write_list(names: list[str], path: Path) -> None:
    root = ET.Element("StreamingFileList")

    ET.SubElement(root, "ListFormatVersion").text = "1.0"
    ET.SubElement(root, "NumOfFiles").text = str(len(names))

    files = ET.SubElement(root, "Files")

    for name in names:
        file_node = ET.SubElement(files, "File")
        ET.SubElement(file_node, "Name").text = name

    ET.indent(root, space="    ")

    ET.ElementTree(root).write(
        path,
        encoding="UTF-8",
        xml_declaration=True,
    )


def main() -> None:
    print("w_value 문자열을 붙여넣으세요.")
    print("입력이 끝나면 새 줄에 q 또는 Q를 입력하세요.\n")

    lines = []

    while True:
        try:
            line = input()
        except EOFError:
            break

        if line.strip().lower() == "q":
            break

        lines.append(line)

    names = extract_names("\n".join(lines))

    write_list(names, OUTPUT)

    print(f"\n[생성 완료] {OUTPUT}")
    print(f"[영상 개수] {len(names)}")

    for i, name in enumerate(names, 1):
        print(f"{i}. {name}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print(f"[오류] {exc}")
        raise SystemExit(1)
