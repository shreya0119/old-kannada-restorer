import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional
from bs4 import BeautifulSoup


def extract_word_confidence_from_djvu(
    djvu_xml_path: str,
    target_words: List[str]
) -> None:
    """
    Parses DjVu XML file and prints occurrences of target words along with
    their confidence scores / attributes.
    """
    tree = ET.parse(djvu_xml_path)
    root = tree.getroot()

    print("--- First 3 XML Elements Sample ---")
    sample_count = 0
    for elem in root.iter():
        if elem.text and elem.text.strip():
            print(f"Tag: {elem.tag} | Attribs: {elem.attrib} | Text: {elem.text.strip()}")
            sample_count += 1
            if sample_count >= 3:
                break
    print("-----------------------------------")

    target_set = {word.strip().lower() for word in target_words}

    found_count = 0
    for elem in root.iter():
        text = (elem.text or "").strip()
        if text and text.lower() in target_set:
            confidence = (
                elem.attrib.get("x-confidence")
                or elem.attrib.get("confidence")
                or elem.attrib.get("coords")
                or "N/A"
            )
            attribs = " ".join(f'{k}="{v}"' for k, v in elem.attrib.items())
            print(f"Word: '{text}' | Attributes: {attribs} | Confidence/Coords: {confidence}")
            found_count += 1

    if found_count == 0 and target_words:
        print(f"No occurrences found for target words: {target_words}")


def extract_hocr_text_lines(
    hocr_path: str,
    start_marker: Optional[str] = None,
    end_marker: Optional[str] = None
) -> str:
    """
    Parses hOCR HTML file using BeautifulSoup ('lxml' parser) and extracts line-level text,
    optionally bounded by start_marker and end_marker text.
    """
    with open(hocr_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    all_lines = []
    ocr_lines = soup.find_all(class_="ocr_line")

    for line in ocr_lines:
        text = " ".join(line.get_text().split())
        if text:
            all_lines.append(text)

    start_marker_clean = start_marker.strip().lower() if start_marker and start_marker.strip() else None
    end_marker_clean = end_marker.strip().lower() if end_marker and end_marker.strip() else None

    if not start_marker_clean and not end_marker_clean:
        return "\n".join(all_lines)

    lines = []
    extracting = start_marker_clean is None

    for text in all_lines:
        text_lower = text.lower()

        if not extracting and start_marker_clean and start_marker_clean in text_lower:
            extracting = True
            continue

        if extracting and end_marker_clean and end_marker_clean in text_lower:
            break

        if extracting:
            lines.append(text)

    if not lines and all_lines:
        return "\n".join(all_lines)

    return "\n".join(lines)


def search_inscriptions(extracted_text_path: str, query_keyword: str) -> None:
    """
    Reads extracted text file, groups text into non-empty blocks/chunks,
    searches for query_keyword (case-insensitive), and prints matching chunks.
    """
    path = Path(extracted_text_path)
    if not path.exists():
        print(f"File not found: {path.resolve()}")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = [block.strip() for block in content.split("\n\n") if block.strip()]
    query_lower = query_keyword.lower()

    matches = []
    for idx, block in enumerate(blocks):
        if query_lower in block.lower():
            matches.append((idx, block))

    print(f"Found {len(matches)} matching block(s) for query '{query_keyword}':\n")
    for idx, block in matches:
        print(f"--- Block #{idx + 1} ---")
        print(block)
        print("-" * 25)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

    parser = argparse.ArgumentParser(description="Extract text between markers from hOCR file.")
    parser.add_argument(
        "--hocr",
        type=str,
        default=str(BASE_DIR / "epigraphiacarnat09myso_hocr.html"),
        help="Path to hOCR file",
    )
    parser.add_argument("--start", type=str, default="", help="Start heading marker")
    parser.add_argument("--end", type=str, default="", help="End heading marker")
    parser.add_argument(
        "--out",
        type=str,
        default=str(BASE_DIR / "extracted_text.txt"),
        help="Output file path",
    )
    parser.add_argument("--words", nargs="+", help="Target words to check OCR confidence in DjVu XML")
    parser.add_argument("--djvu", type=str, default=str(BASE_DIR / "epigraphiacarnat09myso_djvu.xml"), help="Path to DjVu XML file")

    args = parser.parse_args()

    input_path = Path(args.hocr).resolve()
    output_path = Path(args.out).resolve()

    if input_path.exists():
        extracted = extract_hocr_text_lines(
            str(input_path),
            start_marker=args.start,
            end_marker=args.end,
        )

        output_lines = [line for line in extracted.splitlines() if line.strip()]
        print(f"Total lines extracted: {len(output_lines)}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(extracted)
        print(f"Extracted text saved to {output_path}")
    else:
        print(f"File not found: {input_path}")

    if args.words:
        djvu_path = Path(args.djvu).resolve()
        if djvu_path.exists():
            extract_word_confidence_from_djvu(str(djvu_path), args.words)
        else:
            print(f"DjVu file not found: {djvu_path}")
