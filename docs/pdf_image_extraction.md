# PDF Illustration Extraction Helper

## Overview

`extract_pdf_illustrations.py` walks one or more PDF files, exports embedded images and
illustrations, and names them with caption-like text it discovers nearby. It is tuned to:

- skip full-page scans by default (so you avoid exporting entire bitmap pages)
- ignore tiny icons via a minimum edge threshold
- prefer captions immediately below an image, with fallbacks to other nearby text
- generate filesystem-safe filenames using that contextual text

Install the dependency once before running:

```
pip install pymupdf
```

## Basic Usage

```
python3 extract_pdf_illustrations.py /path/to/pdfs --output extracted_images
```

- You can pass a single PDF file or a directory; directories are searched recursively.
- Output is grouped per source document under the chosen `--output` directory.

## Key Options

- `--context-margin`: points (1/72") to scan for captions; enlarge if captions sit farther away.
- `--max-context-words`: trims caption text before slugifying filenames.
- `--full-page-threshold`: ratio of page area that qualifies as a full-page scan.
- `--include-full-page`: export full-page scans instead of skipping them.
- `--min-edge`: filters out images with a small shortest edge (default 48pt ≈ 0.67").
- `--log-level`: set to `DEBUG` for per-image diagnostics.

Run `python3 extract_pdf_illustrations.py --help` for the complete CLI reference.

## Output Layout

```
extracted_images/
 └── source-document-name/
     ├── context-derived-name-1.png
     ├── context-derived-name-2.jpg
     └── page-003-image-02.png  # falls back when no caption found
```

## Verification Checklist

- Sample a few exported images per PDF and confirm they are meaningful figures, not full pages.
- Compare filenames against nearby text in the PDF to ensure captions look sensible.
- If expected images are missing, re-run with a larger `--context-margin` or lower `--min-edge`.
- For documents that are entirely scanned pages, re-run with `--include-full-page` to export them.
- Keep `--log-level DEBUG` handy—it reports skipped images and why they were skipped.

## Troubleshooting

- **Dependency missing**: install PyMuPDF (`pip install pymupdf`).
- **Incorrect caption text**: widen the context margin or increase `--max-context-words`.
- **Too many files**: raise `--min-edge` (e.g., 96) to eliminate small decorative icons.
- **Duplicate filenames**: the script auto-appends counters, but you can delete unwanted results and rerun.

