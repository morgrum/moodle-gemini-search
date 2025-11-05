#!/bin/bash
# Example usage scenarios for the PDF Image Extractor

echo "==================================="
echo "PDF Image Extractor - Example Usage"
echo "==================================="
echo ""

# Example 1: Single PDF file
echo "Example 1: Extract from a single PDF"
echo "Command: python extract_pdf_images.py document.pdf"
echo ""

# Example 2: Directory of PDFs
echo "Example 2: Process all PDFs in a directory (recursive)"
echo "Command: python extract_pdf_images.py /path/to/pdf/library/"
echo ""

# Example 3: Custom output directory
echo "Example 3: Specify output directory"
echo "Command: python extract_pdf_images.py document.pdf -o my_images"
echo ""

# Example 4: Adjust filtering for scanned documents
echo "Example 4: More aggressive scan filtering"
echo "Command: python extract_pdf_images.py document.pdf --max-coverage 0.7"
echo ""

# Example 5: Extract smaller images
echo "Example 5: Include smaller images"
echo "Command: python extract_pdf_images.py document.pdf --min-width 50 --min-height 50"
echo ""

# Example 6: Quiet mode for batch processing
echo "Example 6: Quiet mode (minimal output)"
echo "Command: python extract_pdf_images.py /path/to/pdfs/ -q"
echo ""

# Example 7: More context for better naming
echo "Example 7: Extract more context for naming"
echo "Command: python extract_pdf_images.py document.pdf --context-chars 400"
echo ""

# Example 8: Process only current directory
echo "Example 8: Don't process subdirectories"
echo "Command: python extract_pdf_images.py /path/to/pdfs/ --no-recursive"
echo ""

echo "==================================="
echo "For full help, run:"
echo "python extract_pdf_images.py --help"
echo "==================================="
