#!/usr/bin/env python3
"""Extract figures and images from PDFs with context-aware naming.

This script walks one or more PDF files, extracts embedded raster images and
vector drawings (such as charts), skips full-page scans, and saves the results
as image files named using nearby text context.

The implementation relies on PyMuPDF (``fitz``). Install dependencies with:

    pip install pymupdf

Example usage:

    python extract_pdf_figures.py --input /path/to/pdfs --output ./figures

"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

try:
    import fitz  # type: ignore
except ImportError as exc:
    raise SystemExit(
        "PyMuPDF (fitz) is required. Install it with `pip install pymupdf`."
    ) from exc


# ---------------------------------------------------------------------------
# Configuration data structures


@dataclass
class ExtractionOptions:
    """Collection of tunable extraction parameters."""

    context_margin: float = 48.0  # points (~0.66 in) around figure for context
    context_words: int = 20  # maximum number of words to use for naming
    min_area_ratio: float = 0.01  # ignore tiny graphics (<1% of page area)
    full_page_ratio: float = 0.9  # treat >90% page coverage as full-page scan
    drawing_clip_padding: float = 8.0  # padding around drawing regions
    drawing_scale: float = 2.0  # render drawings at 2x resolution


# ---------------------------------------------------------------------------
# Utility helpers


FILENAME_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9]+")


def iter_pdf_files(input_path: Path) -> Iterable[Path]:
    """Yield PDF files from *input_path* (file or directory)."""

    if input_path.is_file():
        if input_path.suffix.lower() == ".pdf":
            yield input_path
        else:
            logging.debug("Skipping non-PDF file: %s", input_path)
        return

    for path in sorted(input_path.rglob("*.pdf")):
        if path.is_file():
            yield path


def sanitize_snippet(snippet: str, fallback: str, max_length: int = 80) -> str:
    """Return a filesystem-safe slug derived from *snippet*.

    ``fallback`` is used if no valid characters remain.
    """

    snippet = snippet.strip()
    if not snippet:
        snippet = fallback

    normalized = FILENAME_SAFE_PATTERN.sub("-", snippet)
    normalized = normalized.strip("-").lower()

    if not normalized:
        normalized = fallback

    if len(normalized) > max_length:
        normalized = normalized[:max_length].rstrip("-")

    return normalized or fallback


def words_near_rect(
    words: Sequence[Sequence],
    rect: fitz.Rect,
    margin: float,
    max_words: int,
) -> str:
    """Collect nearby words for context.

    *words* should be the result of ``page.get_text("words")``. Each entry is
    ``(x0, y0, x1, y1, text, block_no, line_no, word_no)``.

    Returns a string with up to *max_words* words.
    """

    expanded = fitz.Rect(rect)
    expanded.x0 -= margin
    expanded.y0 -= margin
    expanded.x1 += margin
    expanded.y1 += margin

    nearby = [w for w in words if fitz.Rect(w[:4]).intersects(expanded)]

    if not nearby:
        # Fallback: words immediately below the rectangle (likely captions)
        caption_band = fitz.Rect(rect.x0, rect.y1, rect.x1, rect.y1 + margin * 2)
        nearby = [w for w in words if fitz.Rect(w[:4]).intersects(caption_band)]

    if not nearby:
        return ""

    nearby.sort(key=lambda w: (w[1], w[0]))  # sort by top then left
    text = " ".join(w[4] for w in nearby[:max_words])

    return text.strip()


def area_ratio(rect: fitz.Rect, page_rect: fitz.Rect) -> float:
    """Return area ratio of *rect* relative to the page rectangle."""

    if rect.is_empty or page_rect.is_empty:
        return 0.0

    return (rect.width * rect.height) / (page_rect.width * page_rect.height)


def ensure_pixmap_rgb(pix: fitz.Pixmap) -> fitz.Pixmap:
    """Convert a PyMuPDF Pixmap to RGB if required."""

    if pix.colorspace is not None and pix.colorspace.n in {3, 4} and not pix.alpha:
        return pix

    if pix.alpha:
        pix = fitz.Pixmap(pix, 0)  # remove alpha channel

    if pix.colorspace is None or pix.colorspace.n not in {3, 4}:
        pix = fitz.Pixmap(fitz.csRGB, pix)

    return pix


# ---------------------------------------------------------------------------
# Core extraction logic


def extract_images_from_page(
    doc: fitz.Document,
    page: fitz.Page,
    output_dir: Path,
    base_name: str,
    options: ExtractionOptions,
    saved_regions: List[Tuple[fitz.Rect, Path]],
) -> int:
    """Extract embedded raster images from *page*.

    Returns the number of exported figures.
    """

    count = 0
    words = page.get_text("words")
    page_rect = page.rect

    raw_dict = page.get_text("dict")
    for block in raw_dict.get("blocks", []):
        if block.get("type") != 1:
            continue

        rect = fitz.Rect(block["bbox"])

        if area_ratio(rect, page_rect) >= options.full_page_ratio:
            logging.info(
                "Skipping full-page scan on %s page %s", base_name, page.number + 1
            )
            continue

        if area_ratio(rect, page_rect) < options.min_area_ratio:
            continue

        xref = block.get("xref")
        if xref is None:
            image_info = block.get("image")
            if isinstance(image_info, dict):
                xref = image_info.get("xref")
            elif isinstance(image_info, list) and image_info:
                xref = image_info[0].get("xref")

        if xref is None:
            logging.debug(
                "Could not determine xref for image block on page %s", page.number + 1
            )
            continue

        try:
            pix = fitz.Pixmap(doc, xref)
        except RuntimeError as exc:  # image stream might be missing
            logging.warning("Failed to load image xref %s: %s", xref, exc)
            continue

        pix = ensure_pixmap_rgb(pix)

        context = words_near_rect(words, rect, options.context_margin, options.context_words)
        snippet = context or f"page-{page.number + 1}"
        slug = sanitize_snippet(snippet, f"page-{page.number + 1}")

        filename = f"{base_name}_p{page.number + 1:03d}_img{count + 1:02d}_{slug}.png"
        out_path = output_dir / filename

        pix.save(out_path)
        count += 1
        saved_regions.append((rect, out_path))

    return count


def extract_drawings_from_page(
    page: fitz.Page,
    output_dir: Path,
    base_name: str,
    options: ExtractionOptions,
    saved_regions: List[Tuple[fitz.Rect, Path]],
    start_index: int,
) -> int:
    """Render vector drawing regions (charts, diagrams) as images."""

    count = 0
    words = page.get_text("words")
    page_rect = page.rect

    for idx, drawing in enumerate(page.get_drawings()):
        rect_data = drawing.get("rect") or drawing.get("bbox")
        if not rect_data:
            continue

        rect = fitz.Rect(rect_data)

        if rect.is_empty:
            continue

        if area_ratio(rect, page_rect) >= options.full_page_ratio:
            continue

        if area_ratio(rect, page_rect) < options.min_area_ratio:
            continue

        padded = fitz.Rect(rect)
        padded.x0 = max(page_rect.x0, padded.x0 - options.drawing_clip_padding)
        padded.y0 = max(page_rect.y0, padded.y0 - options.drawing_clip_padding)
        padded.x1 = min(page_rect.x1, padded.x1 + options.drawing_clip_padding)
        padded.y1 = min(page_rect.y1, padded.y1 + options.drawing_clip_padding)

        # Skip if this drawing substantially overlaps with an already saved region
        if any(padded.intersects(saved_rect) for saved_rect, _ in saved_regions):
            continue

        matrix = fitz.Matrix(options.drawing_scale, options.drawing_scale)

        try:
            pix = page.get_pixmap(matrix=matrix, clip=padded, alpha=False)
        except RuntimeError as exc:
            logging.debug("Failed to render drawing %s on page %s: %s", idx, page.number + 1, exc)
            continue

        context = words_near_rect(words, padded, options.context_margin, options.context_words)
        snippet = context or f"page-{page.number + 1}"
        slug = sanitize_snippet(snippet, f"page-{page.number + 1}")

        sequence = start_index + count + 1
        filename = f"{base_name}_p{page.number + 1:03d}_fig{sequence:02d}_{slug}.png"
        out_path = output_dir / filename
        pix.save(out_path)

        saved_regions.append((padded, out_path))
        count += 1

    return count


def extract_figures_from_pdf(pdf_path: Path, output_root: Path, options: ExtractionOptions) -> int:
    """Process a single PDF file and return the number of figures exported."""

    logging.info("Processing %s", pdf_path)

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:  # pragma: no cover - fitz raises RuntimeError / ValueError
        logging.error("Failed to open %s: %s", pdf_path, exc)
        return 0

    base_name = pdf_path.stem
    pdf_output_dir = output_root / base_name
    pdf_output_dir.mkdir(parents=True, exist_ok=True)

    exported = 0

    for page in doc:
        saved_regions: List[Tuple[fitz.Rect, Path]] = []

        exported += extract_images_from_page(
            doc=doc,
            page=page,
            output_dir=pdf_output_dir,
            base_name=base_name,
            options=options,
            saved_regions=saved_regions,
        )

        exported += extract_drawings_from_page(
            page=page,
            output_dir=pdf_output_dir,
            base_name=base_name,
            options=options,
            saved_regions=saved_regions,
            start_index=exported,
        )

    doc.close()
    return exported


# ---------------------------------------------------------------------------
# CLI entry point


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Path to a PDF file or a directory containing PDF files.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Directory where extracted figures will be saved.",
    )
    parser.add_argument(
        "--context-words",
        type=int,
        default=ExtractionOptions.context_words,
        help="Maximum number of words to use when building file names (default: %(default)s).",
    )
    parser.add_argument(
        "--context-margin",
        type=float,
        default=ExtractionOptions.context_margin,
        help="Margin in points around figures when searching for context (default: %(default)s).",
    )
    parser.add_argument(
        "--min-area-ratio",
        type=float,
        default=ExtractionOptions.min_area_ratio,
        help="Ignore graphics smaller than this fraction of the page area (default: %(default)s).",
    )
    parser.add_argument(
        "--full-page-ratio",
        type=float,
        default=ExtractionOptions.full_page_ratio,
        help="Skip graphics covering more than this fraction of the page area (default: %(default)s).",
    )
    parser.add_argument(
        "--drawing-scale",
        type=float,
        default=ExtractionOptions.drawing_scale,
        help="Scaling factor used when rasterising vector drawings (default: %(default)s).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: %(default)s).",
    )

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")

    options = ExtractionOptions(
        context_words=args.context_words,
        context_margin=args.context_margin,
        min_area_ratio=args.min_area_ratio,
        full_page_ratio=args.full_page_ratio,
        drawing_scale=args.drawing_scale,
    )

    if not args.input.exists():
        logging.error("Input path does not exist: %s", args.input)
        return 1

    args.output.mkdir(parents=True, exist_ok=True)

    total_figures = 0
    pdf_files = list(iter_pdf_files(args.input))

    if not pdf_files:
        logging.warning("No PDF files found under %s", args.input)
        return 0

    for pdf_file in pdf_files:
        total_figures += extract_figures_from_pdf(pdf_file, args.output, options)

    logging.info("Exported %s figures.", total_figures)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
