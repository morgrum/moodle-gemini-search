#!/usr/bin/env python3
"""
Enhanced PDF Image Extractor

This script extracts meaningful images and illustrations from PDF files,
filtering out full-page scans and naming images based on surrounding text context.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import fitz  # PyMuPDF
from PIL import Image
import io
import hashlib


class PDFImageExtractor:
    def __init__(self, 
                 output_dir: str = "extracted_images",
                 min_width: int = 100,
                 min_height: int = 100,
                 max_page_coverage: float = 0.85,
                 context_chars: int = 200):
        """
        Initialize the PDF image extractor.
        
        Args:
            output_dir: Directory to save extracted images
            min_width: Minimum image width in pixels (filters tiny images)
            min_height: Minimum image height in pixels (filters tiny images)
            max_page_coverage: Maximum portion of page an image can cover (0-1)
                              Images covering more than this are likely full-page scans
            context_chars: Number of characters to extract before/after image for naming
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.min_width = min_width
        self.min_height = min_height
        self.max_page_coverage = max_page_coverage
        self.context_chars = context_chars
        self.extracted_count = 0
        self.skipped_count = 0
        
    def is_full_page_scan(self, img_bbox: Tuple, page_bbox: Tuple) -> bool:
        """
        Determine if an image is likely a full-page scan.
        
        Args:
            img_bbox: Image bounding box (x0, y0, x1, y1)
            page_bbox: Page bounding box (x0, y0, x1, y1)
            
        Returns:
            True if image appears to be a full-page scan
        """
        img_width = img_bbox[2] - img_bbox[0]
        img_height = img_bbox[3] - img_bbox[1]
        page_width = page_bbox[2] - page_bbox[0]
        page_height = page_bbox[3] - page_bbox[1]
        
        img_area = img_width * img_height
        page_area = page_width * page_height
        
        if page_area == 0:
            return False
            
        coverage = img_area / page_area
        
        # If image covers more than threshold of the page, it's likely a scan
        return coverage > self.max_page_coverage
    
    def extract_text_context(self, page, img_bbox: Tuple) -> str:
        """
        Extract text near the image for contextual naming.
        
        Args:
            page: PyMuPDF page object
            img_bbox: Image bounding box (x0, y0, x1, y1)
            
        Returns:
            Cleaned text context around the image
        """
        # Get text from areas near the image
        contexts = []
        
        # Text above image
        above_rect = fitz.Rect(
            img_bbox[0],
            max(0, img_bbox[1] - 100),
            img_bbox[2],
            img_bbox[1]
        )
        
        # Text below image
        below_rect = fitz.Rect(
            img_bbox[0],
            img_bbox[3],
            img_bbox[2],
            min(page.rect.height, img_bbox[3] + 100)
        )
        
        # Text to the left
        left_rect = fitz.Rect(
            max(0, img_bbox[0] - 150),
            img_bbox[1],
            img_bbox[0],
            img_bbox[3]
        )
        
        # Text to the right
        right_rect = fitz.Rect(
            img_bbox[2],
            img_bbox[1],
            min(page.rect.width, img_bbox[2] + 150),
            img_bbox[3]
        )
        
        # Extract text from each region
        for rect in [above_rect, below_rect, left_rect, right_rect]:
            text = page.get_text("text", clip=rect).strip()
            if text:
                contexts.append(text)
        
        # Combine all contexts
        full_context = " ".join(contexts)
        
        # Clean and limit the context
        full_context = " ".join(full_context.split())  # Remove extra whitespace
        full_context = full_context[:self.context_chars]
        
        return full_context
    
    def generate_filename(self, context: str, page_num: int, img_index: int, 
                         pdf_name: str) -> str:
        """
        Generate a meaningful filename based on context.
        
        Args:
            context: Text context around the image
            page_num: Page number
            img_index: Image index on the page
            pdf_name: Name of the source PDF
            
        Returns:
            Generated filename
        """
        # Clean the PDF name
        clean_pdf_name = re.sub(r'[^\w\s-]', '', pdf_name)
        clean_pdf_name = re.sub(r'[-\s]+', '_', clean_pdf_name)
        
        if context:
            # Extract meaningful words from context
            # Look for capitalized words, potential titles, figure numbers
            words = context.split()
            
            # Try to find figure/table numbers
            fig_pattern = r'(?i)(figure|fig|table|chart|diagram|illustration)\s*(\d+\.?\d*)'
            fig_match = re.search(fig_pattern, context)
            
            if fig_match:
                prefix = fig_match.group(1).lower()
                number = fig_match.group(2).replace('.', '_')
                base_name = f"{prefix}_{number}"
            else:
                # Extract up to 5 meaningful words
                meaningful_words = []
                for word in words[:15]:  # Check first 15 words
                    # Clean word
                    clean_word = re.sub(r'[^\w]', '', word)
                    # Keep words that are:
                    # - Capitalized
                    # - Longer than 3 characters
                    # - Not common words
                    if (clean_word and 
                        len(clean_word) > 3 and
                        clean_word[0].isupper() and
                        clean_word.lower() not in ['the', 'this', 'that', 'with', 'from', 'have']):
                        meaningful_words.append(clean_word)
                    
                    if len(meaningful_words) >= 5:
                        break
                
                if meaningful_words:
                    base_name = "_".join(meaningful_words[:5])
                else:
                    # Fallback to first few words
                    base_name = "_".join([re.sub(r'[^\w]', '', w) for w in words[:5] if w])
            
            # Truncate if too long
            if len(base_name) > 50:
                base_name = base_name[:50]
            
            base_name = base_name.strip('_')
        else:
            base_name = f"{clean_pdf_name}_page{page_num}"
        
        # Ensure uniqueness with page and image index
        filename = f"{base_name}_p{page_num}_i{img_index}"
        
        return filename
    
    def extract_images_from_pdf(self, pdf_path: str, verbose: bool = True) -> int:
        """
        Extract images from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            verbose: Print progress information
            
        Returns:
            Number of images extracted
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            print(f"Error: PDF file not found: {pdf_path}")
            return 0
        
        pdf_name = pdf_path.stem
        pdf_output_dir = self.output_dir / pdf_name
        pdf_output_dir.mkdir(exist_ok=True)
        
        if verbose:
            print(f"\nProcessing: {pdf_path.name}")
        
        doc = fitz.open(pdf_path)
        images_extracted = 0
        images_skipped = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            if verbose and image_list:
                print(f"  Page {page_num + 1}: Found {len(image_list)} image(s)")
            
            for img_index, img_info in enumerate(image_list):
                try:
                    xref = img_info[0]
                    
                    # Get image bbox (position on page)
                    img_rects = page.get_image_rects(xref)
                    if not img_rects:
                        continue
                    
                    img_bbox = img_rects[0]  # Use first occurrence
                    
                    # Check if it's a full-page scan
                    if self.is_full_page_scan(img_bbox, page.rect):
                        if verbose:
                            print(f"    Image {img_index + 1}: Skipped (full-page scan)")
                        images_skipped += 1
                        continue
                    
                    # Extract the image
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Check image dimensions
                    img = Image.open(io.BytesIO(image_bytes))
                    width, height = img.size
                    
                    if width < self.min_width or height < self.min_height:
                        if verbose:
                            print(f"    Image {img_index + 1}: Skipped (too small: {width}x{height})")
                        images_skipped += 1
                        continue
                    
                    # Extract text context
                    context = self.extract_text_context(page, img_bbox)
                    
                    # Generate filename
                    filename = self.generate_filename(
                        context, 
                        page_num + 1, 
                        img_index + 1,
                        pdf_name
                    )
                    
                    # Save the image
                    output_path = pdf_output_dir / f"{filename}.{image_ext}"
                    
                    # Handle duplicate filenames
                    counter = 1
                    while output_path.exists():
                        output_path = pdf_output_dir / f"{filename}_{counter}.{image_ext}"
                        counter += 1
                    
                    with open(output_path, "wb") as f:
                        f.write(image_bytes)
                    
                    images_extracted += 1
                    
                    if verbose:
                        context_preview = context[:60] + "..." if len(context) > 60 else context
                        print(f"    Image {img_index + 1}: ✓ Saved as {output_path.name}")
                        if context_preview:
                            print(f"      Context: {context_preview}")
                        print(f"      Size: {width}x{height}")
                
                except Exception as e:
                    if verbose:
                        print(f"    Image {img_index + 1}: Error - {str(e)}")
                    continue
        
        doc.close()
        
        if verbose:
            print(f"  Summary: {images_extracted} extracted, {images_skipped} skipped\n")
        
        self.extracted_count += images_extracted
        self.skipped_count += images_skipped
        
        return images_extracted
    
    def process_directory(self, directory: str, recursive: bool = True, 
                         verbose: bool = True) -> Dict[str, int]:
        """
        Process all PDF files in a directory.
        
        Args:
            directory: Directory containing PDF files
            recursive: Process subdirectories recursively
            verbose: Print progress information
            
        Returns:
            Dictionary with processing statistics
        """
        directory = Path(directory)
        
        if not directory.exists():
            print(f"Error: Directory not found: {directory}")
            return {"total_pdfs": 0, "total_images": 0, "total_skipped": 0}
        
        # Find all PDF files
        if recursive:
            pdf_files = list(directory.rglob("*.pdf"))
        else:
            pdf_files = list(directory.glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {directory}")
            return {"total_pdfs": 0, "total_images": 0, "total_skipped": 0}
        
        print(f"Found {len(pdf_files)} PDF file(s)")
        print(f"Output directory: {self.output_dir.absolute()}")
        print("=" * 70)
        
        for pdf_file in pdf_files:
            self.extract_images_from_pdf(pdf_file, verbose=verbose)
        
        print("=" * 70)
        print(f"Processing complete!")
        print(f"Total images extracted: {self.extracted_count}")
        print(f"Total images skipped: {self.skipped_count}")
        print(f"Output location: {self.output_dir.absolute()}")
        
        return {
            "total_pdfs": len(pdf_files),
            "total_images": self.extracted_count,
            "total_skipped": self.skipped_count
        }


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract meaningful images from PDF files with contextual naming",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract images from a single PDF
  python extract_pdf_images.py document.pdf
  
  # Process all PDFs in a directory
  python extract_pdf_images.py /path/to/pdfs/
  
  # Customize output and filtering
  python extract_pdf_images.py /path/to/pdfs/ -o my_images --min-width 200 --max-coverage 0.9
  
  # Process only current directory (not subdirectories)
  python extract_pdf_images.py /path/to/pdfs/ --no-recursive
        """
    )
    
    parser.add_argument(
        "input",
        help="PDF file or directory containing PDF files"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="extracted_images",
        help="Output directory for extracted images (default: extracted_images)"
    )
    
    parser.add_argument(
        "--min-width",
        type=int,
        default=100,
        help="Minimum image width in pixels (default: 100)"
    )
    
    parser.add_argument(
        "--min-height",
        type=int,
        default=100,
        help="Minimum image height in pixels (default: 100)"
    )
    
    parser.add_argument(
        "--max-coverage",
        type=float,
        default=0.85,
        help="Maximum page coverage ratio for images (0-1, default: 0.85). "
             "Images covering more than this are treated as full-page scans."
    )
    
    parser.add_argument(
        "--context-chars",
        type=int,
        default=200,
        help="Number of characters to extract for context (default: 200)"
    )
    
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't process subdirectories recursively"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode (minimal output)"
    )
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = PDFImageExtractor(
        output_dir=args.output,
        min_width=args.min_width,
        min_height=args.min_height,
        max_page_coverage=args.max_coverage,
        context_chars=args.context_chars
    )
    
    input_path = Path(args.input)
    
    # Process input
    if input_path.is_file():
        if input_path.suffix.lower() == '.pdf':
            extractor.extract_images_from_pdf(input_path, verbose=not args.quiet)
        else:
            print(f"Error: {input_path} is not a PDF file")
            sys.exit(1)
    elif input_path.is_dir():
        extractor.process_directory(
            input_path, 
            recursive=not args.no_recursive,
            verbose=not args.quiet
        )
    else:
        print(f"Error: {input_path} does not exist")
        sys.exit(1)


if __name__ == "__main__":
    main()
