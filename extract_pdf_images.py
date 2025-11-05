#!/usr/bin/env python3
"""
Extract images and illustrations from PDF files with intelligent naming based on context.

This script:
- Extracts actual images/illustrations from PDFs (not whole pages)
- Handles both scanned PDFs (bitmap) and PDFs with text layers
- Names images based on meaningful surrounding text context
- Preserves images without embedding text in them
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import argparse

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is required. Install with: pip install pymupdf")
    sys.exit(1)

try:
    from PIL import Image
    import io
except ImportError:
    print("Error: Pillow is required. Install with: pip install pillow")
    sys.exit(1)


def sanitize_filename(text: str, max_length: int = 100) -> str:
    """Convert text to a safe filename."""
    if not text:
        return "image"
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove or replace invalid filename characters
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    
    # Remove leading/trailing dots and spaces
    text = text.strip('. ')
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0]  # Cut at word boundary
    
    return text if text else "image"


def extract_text_near_image(page: fitz.Page, bbox: fitz.Rect, context_lines: int = 5) -> str:
    """Extract text context around an image's location."""
    try:
        # Get text blocks from the page
        text_blocks = page.get_text("blocks")
        
        if not text_blocks:
            return ""
        
        # Find text blocks near the image
        nearby_text = []
        
        for block in text_blocks:
            # block format: (x0, y0, x1, y1, text, block_no, block_type)
            if len(block) < 5:
                continue
            
            block_rect = fitz.Rect(block[:4])
            
            # Check if block is above, below, or overlapping with image
            # Consider blocks within reasonable distance (e.g., 50 points)
            margin = 50
            
            # Check vertical proximity
            if (block_rect.y1 < bbox.y0 + margin and block_rect.y0 > bbox.y0 - margin * 2) or \
               (block_rect.y0 > bbox.y1 - margin and block_rect.y1 < bbox.y1 + margin * 2) or \
               (abs(block_rect.y0 - bbox.y0) < margin * 2) or \
               (abs(block_rect.y1 - bbox.y1) < margin * 2):
                
                text = block[4].strip()
                if text and len(text) > 3:  # Ignore very short text
                    nearby_text.append(text)
        
        # Also try to get text from a wider area around the image
        expanded_bbox = fitz.Rect(
            bbox.x0 - 20,
            max(0, bbox.y0 - 100),  # Look above the image
            bbox.x1 + 20,
            min(page.rect.y1, bbox.y1 + 100)  # Look below the image
        )
        
        expanded_text = page.get_text("text", clip=expanded_bbox)
        
        # Combine nearby text blocks and expanded text
        all_text = nearby_text + [expanded_text] if expanded_text else nearby_text
        
        # Clean and combine text
        combined_text = " ".join(all_text)
        
        # Extract meaningful phrases (captions, labels, headings)
        # Look for patterns like "Figure X:", "See image", etc.
        caption_patterns = [
            r'(?:Figure|Fig|Image|Picture|Photo|Chart|Graph|Diagram|Illustration)\s*\d*[:\-]?\s*([^\n\.]{10,80})',
            r'([A-Z][^\.]{15,80})',  # Capitalized sentences (likely headings)
        ]
        
        for pattern in caption_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        # If no caption found, use first meaningful sentence
        sentences = re.split(r'[\.\n]+', combined_text)
        meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 15 and len(s.strip()) < 150]
        
        if meaningful_sentences:
            return meaningful_sentences[0]
        
        # Fallback: use first chunk of text
        if combined_text:
            # Take first 60 characters of meaningful text
            words = combined_text.split()
            result = []
            char_count = 0
            for word in words:
                if char_count + len(word) > 60:
                    break
                result.append(word)
                char_count += len(word) + 1
            return " ".join(result)
        
        return ""
    
    except Exception as e:
        print(f"Warning: Could not extract text context: {e}")
        return ""


def is_scanned_page(page: fitz.Page) -> bool:
    """Determine if a page is a scanned bitmap (no text layer)."""
    try:
        text = page.get_text().strip()
        # If there's very little text relative to page size, it's likely scanned
        text_length = len(text)
        
        # Check if there are actual text blocks (not just OCR artifacts)
        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if len(b) > 4 and len(b[4].strip()) > 10]
        
        # If we have very few or no substantial text blocks, likely scanned
        if len(text_blocks) < 3 and text_length < 100:
            return True
        
        return False
    except:
        return True  # Assume scanned if we can't determine


def extract_images_from_page(page: fitz.Page, page_num: int, doc_name: str) -> List[Tuple[Image.Image, str, dict]]:
    """Extract images from a single PDF page."""
    images = []
    
    try:
        # Get all image objects from the page
        image_list = page.get_images()
        
        if not image_list:
            # Page might be scanned - check if it's a bitmap
            if is_scanned_page(page):
                # For scanned pages, we'll skip whole-page extraction
                # Instead, look for actual embedded images
                pass
            return images
        
        # Extract each image
        for img_index, img in enumerate(image_list):
            try:
                # Get image data
                xref = img[0]
                base_image = page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Skip if image is too small (likely decorative/bullet)
                if base_image.get("width", 0) < 50 or base_image.get("height", 0) < 50:
                    continue
                
                # Convert to PIL Image
                pil_image = Image.open(io.BytesIO(image_bytes))
                
                # Get image location on page
                image_rects = page.get_image_rects(xref)
                
                if not image_rects:
                    # Fallback: try to find image by its position
                    image_rects = [fitz.Rect(0, 0, pil_image.width, pil_image.height)]
                
                # Get text context for naming
                if image_rects:
                    bbox = image_rects[0]  # Use first rect
                    context_text = extract_text_near_image(page, bbox)
                    
                    # Generate filename
                    if context_text:
                        filename_base = sanitize_filename(context_text)
                    else:
                        filename_base = f"{doc_name}_page{page_num + 1}_img{img_index + 1}"
                    
                    # Add page number if multiple images
                    if len(image_list) > 1:
                        filename_base = f"{filename_base}_img{img_index + 1}"
                    
                    images.append((pil_image, filename_base, {
                        "ext": image_ext,
                        "page": page_num + 1,
                        "index": img_index + 1,
                        "context": context_text
                    }))
                
            except Exception as e:
                print(f"Warning: Could not extract image {img_index} from page {page_num + 1}: {e}")
                continue
        
        return images
    
    except Exception as e:
        print(f"Error processing page {page_num + 1}: {e}")
        return []


def extract_images_from_pdf(pdf_path: Path, output_dir: Path, min_size: Tuple[int, int] = (100, 100)) -> None:
    """Extract all images from a PDF file."""
    print(f"\nProcessing: {pdf_path.name}")
    
    # Open PDF
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {e}")
        return
    
    doc_name = pdf_path.stem
    total_images = 0
    
    try:
        # Process each page
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract images from this page
            page_images = extract_images_from_page(page, page_num, doc_name)
            
            # Save each image
            for pil_image, filename_base, metadata in page_images:
                # Skip if image is too small
                if pil_image.width < min_size[0] or pil_image.height < min_size[1]:
                    continue
                
                # Determine file extension
                ext = metadata.get("ext", "png")
                if ext not in ["png", "jpg", "jpeg"]:
                    ext = "png"  # Default to PNG
                
                # Ensure unique filename
                filename = f"{filename_base}.{ext}"
                output_path = output_dir / filename
                
                counter = 1
                while output_path.exists():
                    filename = f"{filename_base}_{counter}.{ext}"
                    output_path = output_dir / filename
                    counter += 1
                
                # Save image
                try:
                    # Convert to RGB if necessary (for JPEG)
                    if ext.lower() in ["jpg", "jpeg"] and pil_image.mode in ["RGBA", "LA", "P"]:
                        rgb_image = Image.new("RGB", pil_image.size, (255, 255, 255))
                        if pil_image.mode == "P":
                            pil_image = pil_image.convert("RGBA")
                        rgb_image.paste(pil_image, mask=pil_image.split()[-1] if pil_image.mode == "RGBA" else None)
                        pil_image = rgb_image
                    
                    pil_image.save(output_path, format=ext.upper() if ext.upper() == "PNG" else "JPEG", quality=95)
                    total_images += 1
                    
                    context_info = f" (context: {metadata['context'][:50]}...)" if metadata.get('context') else ""
                    print(f"  Saved: {filename}{context_info}")
                    
                except Exception as e:
                    print(f"Warning: Could not save image {filename}: {e}")
                    continue
    
    finally:
        doc.close()
    
    print(f"Extracted {total_images} images from {pdf_path.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract images and illustrations from PDF files with intelligent naming"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Input PDF file or directory containing PDF files"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output directory for extracted images (default: 'extracted_images' in input directory)"
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
    
    args = parser.parse_args()
    
    # Resolve input path
    input_path = Path(args.input).resolve()
    
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        sys.exit(1)
    
    # Determine output directory
    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        if input_path.is_file():
            output_dir = input_path.parent / "extracted_images"
        else:
            output_dir = input_path / "extracted_images"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find PDF files
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            print(f"Error: Input file is not a PDF: {input_path}")
            sys.exit(1)
        pdf_files = [input_path]
    else:
        pdf_files = list(input_path.glob("**/*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in: {input_path}")
            sys.exit(1)
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    print(f"Output directory: {output_dir}")
    
    # Process each PDF
    for pdf_file in pdf_files:
        extract_images_from_pdf(
            pdf_file,
            output_dir,
            min_size=(args.min_width, args.min_height)
        )
    
    print(f"\n✓ Extraction complete! Images saved to: {output_dir}")


if __name__ == "__main__":
    main()
