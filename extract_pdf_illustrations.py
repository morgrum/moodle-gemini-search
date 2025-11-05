#!/usr/bin/env python3
"""Extract images and illustration-like content from PDFs and name them using nearby text.

This script walks one or more PDF documents, exports embedded images (figures, photos,
charts, etc.), skips full-page scans by default, and generates descriptive filenames based on
caption-like text found near each image. It is designed to avoid exporting entire scanned
pages as images while still capturing meaningful illustrations.

Requires: PyMuPDF (``pip install pymupdf``)
"""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import fitz  # PyMuPDF


@dataclass
class ExtractionStats:
    pdf_path: Path
    exported: int = 0
    skipped_full_page: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract illustration images from PDFs and name them using nearby text context.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="PDF file or directory containing PDF files",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("extracted_images"),
        help="Directory where extracted images will be written",
    )
    parser.add_argument(
        "--context-margin",
        type=float,
        default=72.0,
        help="Margin (in PDF points) above/below/aside an image to search for caption text (~72 = 1 inch)",
    )
    parser.add_argument(
        "--max-context-words",
        type=int,
        default=12,
        help="Maximum number of words from nearby text to include in filenames",
    )
    parser.add_argument(
        "--full-page-threshold",
        type=float,
        default=0.9,
        help="If image area / page area meets or exceeds this ratio it is treated as a full-page scan",
    )
    parser.add_argument(
        "--include-full-page",
        dest="skip_full_page",
        action="store_false",
        help="Also export images that cover an entire page (scanned pages)",
    )
    parser.set_defaults(skip_full_page=True)
    parser.add_argument(
        "--min-edge",
        type=float,
        default=48.0,
        help="Skip images whose shortest edge is below this size in PDF points (helps avoid tiny icons)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Logging verbosity",
    )
    return parser.parse_args()


def configure_logging(level_name: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level_name.upper(), logging.INFO),
        format="[%(levelname)s] %(message)s",
    )


def iter_pdf_files(root: Path) -> Iterable[Path]:
    if root.is_file() and root.suffix.lower() == ".pdf":
        yield root
        return

    if not root.is_dir():
        logging.warning("No PDFs found: %s is neither a PDF file nor a directory", root)
        return

    for pdf_path in sorted(root.rglob("*.pdf")):
        if pdf_path.is_file():
            yield pdf_path


def extract_for_document(pdf_path: Path, output_root: Path, args: argparse.Namespace) -> ExtractionStats:
    stats = ExtractionStats(pdf_path=pdf_path)
    logging.info("Processing %s", pdf_path)

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:  # pragma: no cover - defensive wrapper
        logging.error("Failed to open %s: %s", pdf_path, exc)
        return stats

    pdf_output_dir = output_root / pdf_path.stem
    pdf_output_dir.mkdir(parents=True, exist_ok=True)

    used_filenames: set[str] = set()

    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        exported, skipped = export_images_from_page(
            doc,
            page,
            pdf_output_dir,
            used_filenames,
            args,
        )
        stats.exported += exported
        stats.skipped_full_page += skipped

    doc.close()

    if stats.exported:
        logging.info(
            "Finished %s → %d images (skipped %d full-page scans)",
            pdf_path.name,
            stats.exported,
            stats.skipped_full_page,
        )
    else:
        logging.info("No images exported from %s", pdf_path.name)

    return stats


def export_images_from_page(
    doc: fitz.Document,
    page: fitz.Page,
    output_dir: Path,
    used_filenames: set[str],
    args: argparse.Namespace,
) -> tuple[int, int]:
    """Export embedded images from a single page.

    Returns a tuple of (exported_count, skipped_full_page_count).
    """

    page_words = page.get_text("words") or []
    page_words_sorted = sorted(page_words, key=lambda w: (w[5], w[6], w[7], w[0]))
    page_dict = page.get_text("dict")
    exported = 0
    skipped_full_page = 0

    blocks: Sequence[dict] = page_dict.get("blocks", [])
    if not blocks:
        return exported, skipped_full_page

    image_occurrence = 0

    for block in blocks:
        if block.get("type") != 1:
            continue

        bbox = fitz.Rect(block.get("bbox", page.rect))
        if min(bbox.width, bbox.height) < args.min_edge:
            logging.debug(
                "Skipping tiny image on page %d (%sx%s)",
                page.number + 1,
                round(bbox.width, 1),
                round(bbox.height, 1),
            )
            continue

        xref = resolve_xref(block.get("image"))
        if not xref:
            logging.debug("No xref found for image block on page %d", page.number + 1)
            continue

        if args.skip_full_page and is_full_page_image(bbox, page.rect, args.full_page_threshold):
            skipped_full_page += 1
            logging.debug(
                "Skipping full-page image (xref %s) on page %d", xref, page.number + 1
            )
            continue

        context_text = extract_context_text(
            page,
            page_words_sorted,
            bbox,
            args.context_margin,
            args.max_context_words,
        )

        fallback_label = f"page-{page.number + 1:03d}-image-{image_occurrence:02d}"
        slug = slugify(context_text) if context_text else fallback_label
        filename = ensure_unique_filename(slug, fallback_label, used_filenames, output_dir)

        try:
            image_bytes, ext = extract_image_bytes(doc, xref)
        except Exception as exc:  # pragma: no cover - defensive wrapper
            logging.error(
                "Failed to extract image xref %s from %s page %d: %s",
                xref,
                doc.name,
                page.number + 1,
                exc,
            )
            continue

        output_path = output_dir / f"{filename}.{ext}"
        output_path.write_bytes(image_bytes)

        exported += 1
        image_occurrence += 1

    return exported, skipped_full_page


def resolve_xref(image_entry) -> int | None:
    if image_entry is None:
        return None
    if isinstance(image_entry, dict):
        for key in ("xref", "id", "number"):
            value = image_entry.get(key)
            if isinstance(value, int):
                return value
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None
    if isinstance(image_entry, int):
        return image_entry
    if isinstance(image_entry, str):
        stripped = re.sub(r"[^0-9]", "", image_entry)
        if stripped.isdigit():
            return int(stripped)
    return None


def is_full_page_image(image_rect: fitz.Rect, page_rect: fitz.Rect, threshold: float) -> bool:
    page_area = page_rect.get_area()
    image_area = image_rect.get_area()
    if page_area == 0:
        return False
    coverage = image_area / page_area
    return coverage >= threshold


def extract_context_text(
    page: fitz.Page,
    words: Sequence[Sequence],
    image_rect: fitz.Rect,
    margin: float,
    max_words: int,
) -> str:
    if not words:
        return ""

    page_rect = page.rect

    candidate_zones = [
        (
            "below",
            fitz.Rect(
                max(page_rect.x0, image_rect.x0 - margin),
                min(page_rect.y1, image_rect.y1),
                min(page_rect.x1, image_rect.x1 + margin),
                min(page_rect.y1, image_rect.y1 + margin),
            ),
        ),
        (
            "above",
            fitz.Rect(
                max(page_rect.x0, image_rect.x0 - margin),
                max(page_rect.y0, image_rect.y0 - margin),
                min(page_rect.x1, image_rect.x1 + margin),
                min(page_rect.y1, image_rect.y0),
            ),
        ),
        (
            "right",
            fitz.Rect(
                min(page_rect.x1, image_rect.x1),
                max(page_rect.y0, image_rect.y0 - margin * 0.25),
                min(page_rect.x1, image_rect.x1 + margin),
                min(page_rect.y1, image_rect.y1 + margin * 0.25),
            ),
        ),
        (
            "left",
            fitz.Rect(
                max(page_rect.x0, image_rect.x0 - margin),
                max(page_rect.y0, image_rect.y0 - margin * 0.25),
                max(page_rect.x0, image_rect.x0),
                min(page_rect.y1, image_rect.y1 + margin * 0.25),
            ),
        ),
    ]

    best_text = ""
    best_distance = float("inf")

    for label, zone in candidate_zones:
        if zone.get_area() <= 0:
            continue
        zone_words = [w for w in words if fitz.Rect(w[0], w[1], w[2], w[3]).intersects(zone)]
        if not zone_words:
            continue
        text = " ".join(w[4] for w in zone_words)
        cleaned = normalize_caption(text, max_words)
        if not cleaned:
            continue

        distance = caption_distance(label, zone, image_rect)
        if distance < best_distance:
            best_distance = distance
            best_text = cleaned

    return best_text


def caption_distance(label: str, zone: fitz.Rect, image_rect: fitz.Rect) -> float:
    if label == "below":
        return abs(zone.y0 - image_rect.y1)
    if label == "above":
        return abs(image_rect.y0 - zone.y1)
    if label == "right":
        return abs(zone.x0 - image_rect.x1)
    if label == "left":
        return abs(image_rect.x0 - zone.x1)
    return float("inf")


def normalize_caption(text: str, max_words: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = cleaned.replace("\xad", "")  # soft hyphen
    if not cleaned:
        return ""
    words = cleaned.split()
    if max_words > 0:
        words = words[:max_words]
    return " ".join(words)


def slugify(text: str, max_length: int = 80) -> str:
    simplified = text.lower()
    simplified = re.sub(r"[^a-z0-9]+", "-", simplified)
    simplified = simplified.strip("-")
    if not simplified:
        return ""
    if len(simplified) > max_length:
        simplified = simplified[:max_length].rstrip("-")
    return simplified


def ensure_unique_filename(
    slug: str,
    fallback: str,
    used_filenames: set[str],
    output_dir: Path,
) -> str:
    base = slug or fallback
    base = base[:120]  # guard against extremely long names
    candidate = base
    counter = 1

    while True:
        filename = candidate
        if filename not in used_filenames and not any(output_dir.glob(f"{filename}.*")):
            used_filenames.add(filename)
            return filename
        counter += 1
        candidate = f"{base}-{counter}"


def extract_image_bytes(doc: fitz.Document, xref: int) -> tuple[bytes, str]:
    image_info = doc.extract_image(xref)
    image_bytes = image_info.get("image")
    ext = image_info.get("ext", "png")
    if not image_bytes:
        raise ValueError(f"No image data returned for xref {xref}")
    if not ext:
        ext = "png"
    ext = ext.lower().strip('.')
    if ext not in {"png", "jpg", "jpeg", "bmp", "ppm", "pbm", "gif"}:
        ext = "png"
    return image_bytes, ext


def ensure_output_root(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)

    output_root = ensure_output_root(args.output)

    pdf_files = list(iter_pdf_files(args.input_path))
    if not pdf_files:
        logging.error("No PDF files found under %s", args.input_path)
        return

    aggregate_exported = 0
    aggregate_skipped = 0

    for pdf_path in pdf_files:
        stats = extract_for_document(pdf_path, output_root, args)
        aggregate_exported += stats.exported
        aggregate_skipped += stats.skipped_full_page

    logging.info(
        "Finished: exported %d images across %d PDFs (skipped %d full-page scans)",
        aggregate_exported,
        len(pdf_files),
        aggregate_skipped,
    )


if __name__ == "__main__":
    main()

