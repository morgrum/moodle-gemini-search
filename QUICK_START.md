# Quick Start Guide - PDF Image Extractor

## Install (One Time)

```bash
pip install PyMuPDF Pillow
```

## Basic Usage

### Extract from one PDF
```bash
python extract_pdf_images.py document.pdf
```

### Extract from a folder of PDFs
```bash
python extract_pdf_images.py /path/to/pdf/folder/
```

## Common Issues & Solutions

### Problem: Getting full-page scans instead of images

**Solution**: Lower the coverage threshold
```bash
python extract_pdf_images.py document.pdf --max-coverage 0.7
```

### Problem: Missing some images (too small)

**Solution**: Lower the minimum size
```bash
python extract_pdf_images.py document.pdf --min-width 50 --min-height 50
```

### Problem: Image names aren't descriptive

**Possible causes**:
1. PDF has no text layer (scanned document without OCR)
2. Text is too far from images

**Solution**: Increase context extraction
```bash
python extract_pdf_images.py document.pdf --context-chars 400
```

## What Gets Skipped?

The script automatically skips:
- ✗ Full-page scans (configurable with `--max-coverage`)
- ✗ Tiny images like logos/icons (configurable with `--min-width/height`)
- ✗ Corrupted or unreadable images

## Where Do Images Go?

```
extracted_images/          ← Output directory
├── Document1/            ← Each PDF gets its own folder
│   ├── figure_1_p3_i1.png
│   └── table_2_p5_i1.jpg
└── Document2/
    └── ...
```

## All Options

```bash
python extract_pdf_images.py --help
```

| Option | What it does | Example |
|--------|-------------|---------|
| `-o DIR` | Output directory | `-o my_images` |
| `--min-width N` | Minimum width (px) | `--min-width 150` |
| `--min-height N` | Minimum height (px) | `--min-height 150` |
| `--max-coverage 0.X` | Max page coverage | `--max-coverage 0.8` |
| `--context-chars N` | Context for naming | `--context-chars 300` |
| `--no-recursive` | Don't go into subdirs | `--no-recursive` |
| `-q` | Quiet mode | `-q` |

## Examples

**Academic papers** (well-labeled figures):
```bash
python extract_pdf_images.py papers/ --min-width 200
```

**Scanned books** (more aggressive filtering):
```bash
python extract_pdf_images.py books/ --max-coverage 0.7
```

**Technical docs** (smaller diagrams):
```bash
python extract_pdf_images.py docs/ --min-width 80
```

## Full Documentation

- **Detailed guide**: `PDF_IMAGE_EXTRACTOR_README.md`
- **What's improved**: `IMPROVEMENTS_SUMMARY.md`
- **More examples**: `example_usage.sh`
