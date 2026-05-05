"""Extract AWL word forms from the original AWL sublists PDF.

Usage:
    python scripts/extract_awl_from_pdf.py /path/to/awlsublists.pdf
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

import fitz

HEADING_RE = re.compile(r"^Sublist\s+(\d+)\s+of\s+(?:the\s+)?Academic\s+Word\s+List$", re.I)
WORD_RE = re.compile(r"^[A-Za-z]+(?:[-'][A-Za-z]+)*$")


def extract_awl_word_forms(pdf_path: Path) -> list[dict]:
    """Return unique AWL word forms with their source sublist."""
    entries = OrderedDict()
    current_sublist = None

    with fitz.open(pdf_path) as doc:
        for page in doc:
            for raw_line in page.get_text().splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                heading = HEADING_RE.match(line)
                if heading:
                    current_sublist = int(heading.group(1))
                    continue

                if current_sublist is None or line.lower().startswith("sublists"):
                    continue

                if WORD_RE.match(line):
                    entries.setdefault(line.lower(), current_sublist)

    return [
        {"word": word, "sublist": sublist}
        for word, sublist in sorted(entries.items(), key=lambda item: (item[1], item[0]))
    ]


def write_outputs(rows: list[dict], data_dir: Path) -> None:
    """Write CSV and JSON versions for inspection and programmatic loading."""
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "awl_word_forms.csv"
    json_path = data_dir / "awl_word_forms.json"

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["word", "sublist"])
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(rows, file, indent=2, ensure_ascii=True)
        file.write("\n")

    print(f"Wrote {len(rows)} AWL word forms to {csv_path} and {json_path}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/extract_awl_from_pdf.py /path/to/awlsublists.pdf")

    rows = extract_awl_word_forms(Path(sys.argv[1]))
    write_outputs(rows, Path("data"))


if __name__ == "__main__":
    main()
