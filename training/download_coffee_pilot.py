"""Download a small, reproducible field-image subset for the Coffee MVP.

Source: Project-AgML/JMuBEN + JMuBEN2 on Hugging Face, originally collected
in Kirinyaga County, Kenya. This is deliberately a development subset, not a
claim of field validation. The script samples across each label range rather
than taking the first repeated rows.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DATASET = "Project-AgML%2Farabica_coffee_leaf_disease_classification"
API = "https://datasets-server.huggingface.co/rows?dataset=" + DATASET + "&config=default&split=train&offset={offset}&length=100"
# Physical row order is not ClassLabel order. It is verified against the
# datasets-server response below, and every downloaded row is checked again.
CLASSES = [
    ("Cerscospora", 0, 0, 7681),
    ("Healthy", 1, 14252, 33235),
    ("Leaf_rust", 2, 33235, 41571),
    ("Miner", 3, 41571, 58549),
    ("Phoma", 4, 7681, 14252),
]


def get_json(url: str) -> dict:
    for attempt in range(6):
        try:
            with urlopen(Request(url, headers={"User-Agent": "CropSignal research MVP"}), timeout=45) as response:
                return json.load(response)
        except (HTTPError, URLError):
            if attempt == 5:
                raise
            time.sleep(min(30, 2 ** attempt * 2))


def download(url: str, target: Path) -> None:
    """Respect the public dataset service rather than hammering it."""
    for attempt in range(6):
        try:
            with urlopen(Request(url, headers={"User-Agent": "CropSignal research MVP"}), timeout=45) as response:
                target.write_bytes(response.read())
            return
        except (HTTPError, URLError) as error:
            if attempt == 5:
                raise
            wait = min(30, 2 ** attempt * 2)
            print(f"Temporary download error ({error}); retrying in {wait}s", flush=True)
            time.sleep(wait)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-class", type=int, default=100)
    parser.add_argument("--output", default="data/coffee-pilot")
    args = parser.parse_args()
    if args.per_class < 20:
        raise SystemExit("Use at least 20 images per class.")
    root = Path(__file__).parents[1] / args.output
    root.mkdir(parents=True, exist_ok=True)
    page_cache: dict[int, dict] = {}
    for label, class_id, start, end in CLASSES:
        folder = root / label
        folder.mkdir(exist_ok=True)
        indices = sorted({start + round(i * (end - start - 1) / (args.per_class - 1)) for i in range(args.per_class)})
        for position, index in enumerate(indices):
            target = folder / f"{position:03d}.jpg"
            if target.exists() and target.stat().st_size > 100:
                continue
            page = index // 100
            if page not in page_cache:
                page_cache[page] = get_json(API.format(offset=page * 100))
            record = next((row["row"] for row in page_cache[page]["rows"] if row["row_idx"] == index), None)
            if not record or record["label"] != class_id:
                raise RuntimeError(f"Unexpected label at row {index}; stop rather than training on an unknown mapping.")
            download(record["image"]["src"], target)
            print(f"{label}: {position + 1}/{len(indices)}", flush=True)
            time.sleep(1.1)
    card = {
        "source": "Project-AgML/arabica_coffee_leaf_disease_classification (JMuBEN/JMuBEN2)",
        "original_collection": "Mutira coffee plantation, Kirinyaga County, Kenya",
        "classes": [item[0] for item in CLASSES],
        "images_per_class_requested": args.per_class,
        "warning": "Development subset only. Source dataset has known duplicates; do not report this split as an external field evaluation.",
    }
    (root / "DATASET_CARD.json").write_text(json.dumps(card, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
