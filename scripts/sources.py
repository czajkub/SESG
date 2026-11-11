"""Shared raw-data handling for the word-list generators.

Everything is downloaded into data/raw/ (gitignored) only if it is missing.
"""

import csv
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

NGSL_URL = "https://www.newgeneralservicelist.com/s/NGSL_12_stats.csv"
SUBTLEX_URL = (
    "https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus/subtlexus1.zip"
)

NGSL = RAW / "NGSL_12_stats.csv"
SUBTLEX_ZIP = RAW / "subtlexus1.zip"
SUBTLEX = RAW / "subtlex_pos.xlsx"

USER_AGENT = "nlp-word-list-generator"


def download(url: str, dest: Path) -> None:
    if dest.exists():
        return
    print(f"downloading {url} -> {dest}", file=sys.stderr)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp, tmp.open("wb") as f:
        shutil.copyfileobj(resp, f)
    tmp.rename(dest)


def download_zip(url: str, zip_dest: Path, extract_to: Path) -> None:
    """Download a zip (if missing) and extract it into extract_to."""
    download(url, zip_dest)
    with zipfile.ZipFile(zip_dest) as z:
        z.extractall(extract_to)


def ngsl_lemmas() -> list[str]:
    """NGSL 1.2 lemmas, most frequent first."""
    download(NGSL_URL, NGSL)
    with NGSL.open(newline="", encoding="utf-8-sig") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: int(r["SFI Rank"]))
    return [r["Lemma"].strip().lower() for r in rows]


def subtlex_dominant_pos() -> dict[str, str]:
    """word -> dominant part of speech in SUBTLEX-US ("Verb", "Noun", "Adjective", ...)."""
    if not SUBTLEX.exists():
        download(SUBTLEX_URL, SUBTLEX_ZIP)
        with zipfile.ZipFile(SUBTLEX_ZIP) as z:
            (name,) = [n for n in z.namelist() if n.endswith(".xlsx")]
            SUBTLEX.write_bytes(z.read(name))
    ws = openpyxl.load_workbook(SUBTLEX, read_only=True).active
    rows = ws.iter_rows(values_only=True)
    header = next(rows)
    w, p = header.index("Word"), header.index("Dom_PoS_SUBTLEX")
    return {str(r[w]).lower(): r[p] for r in rows if r[w] is not None}
