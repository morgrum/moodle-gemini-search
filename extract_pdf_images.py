#!/usr/bin/env python3
"""
Extract embedded images, illustrations, charts, and photos from PDF files.
Names images based on surrounding text context without including text in the image files.
"""

import os
import re
import sys
import hashlib
from pathlib import Path
from typing import List, Tuple, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is required. Install with: pip install PyMuPDF")
    sys.exit(1)


def sanitize_filename(text: str, max_length: int = 100) -> str:
    """Sanitize text to create a valid filename."""
    if not text:
        return "untitled"
    
    # Remove or replace invalid filename characters
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    text = re.sub(r'\s+', '_', text.strip())
    text = re.sub(r'_+', '_', text)
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text or "untitled"


def extract_text_context(page, bbox: Tuple[float, float, float, float], 
                        context_lines: int = 3) -> str:
    """
    Extract text context around an image's bounding box.
    Returns nearby text that can be used for naming.
    """
    # Get all text blocks on the page
    text_blocks = page.get_text("blocks")
    
    if not text_blocks:
        return ""
    
    # Find text blocks that are near the image
    image_top = bbox[1]
    image_bottom = bbox[3]
    image_left = bbox[0]
    image_right = bbox[2]
    
    # Collect text blocks that are above, to the left, or immediately adjacent
    context_parts = []
    
    for block in text_blocks:
        if len(block) < 5:  # Skip if not a proper text block
            continue
        
        block_bbox = block[:4]
        block_text = block[4] if len(block) > 4 else ""
        
        if not block_text or not block_text.strip():
            continue
        
        block_top = block_bbox[1]
        block_bottom = block_bbox[3]
        block_left = block_bbox[0]
        block_right = block_bbox[2]
        
        # Check if block is above the image (within reasonable distance)
        vertical_distance = image_top - block_bottom
        horizontal_overlap = not (block_right < image_left or block_left > image_right)
        
        # Prefer text that's directly above or to the left
        if (vertical_distance >= 0 and vertical_distance < 100 and horizontal_overlap) or \
           (block_bottom < image_bottom and block_right < image_left and 
            (image_left - block_right) < 50):
            context_parts.append((block_top, block_text.strip()))
    
    # Sort by vertical position (top to bottom)
    context_parts.sort(key=lambda x: x[0])
    
    # Take the most relevant context (captions, titles above images)
    if context_parts:
        # Prioritize the block immediately above the image
        relevant_text = context_parts[0][1]
        
        # Clean up the text
        relevant_text = re.sub(r'\s+', ' ', relevant_text)
        relevant_text = relevant_text.strip()
        
        # Limit length for filename
        if len(relevant_text) > 150:
            # Try to find a good breaking point
            sentences = re.split(r'[.!?]\s+', relevant_text)
            if sentences:
                relevant_text = sentences[0]
        
        return relevant_text[:150]
    
    return ""


def extract_images_from_pdf(pdf_path: str, output_dir: str, 
                           min_size: int = 5000) -> List[dict]:
    """
    Extract embedded images from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted images
        min_size: Minimum image size in bytes to filter out small icons/decorations
    
    Returns:
        List of dictionaries with extraction info
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        return []
    
    doc = fitz.open(pdf_path)
    extracted_images = []
    seen_hashes = set()
    
    print(f"\nProcessing: {pdf_path.name}")
    print(f"Total pages: {len(doc)}")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Get list of images on this page
        image_list = page.get_images(full=True)
        
        if not image_list:
            continue
        
        print(f"  Page {page_num + 1}: Found {len(image_list)} image(s)")
        
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                
                # Get image data
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Filter out very small images (likely icons, bullets, decorations)
                if len(image_bytes) < min_size:
                    continue
                
                # Create a hash to avoid duplicates
                image_hash = hashlib.md5(image_bytes).hexdigest()
                if image_hash in seen_hashes:
                    continue
                seen_hashes.add(image_hash)
                
                # Get image position on the page
                image_rects = page.get_image_rects(xref)
                if not image_rects:
                    continue
                
                # Use the first/largest rectangle
                image_bbox = image_rects[0]
                
                # Extract text context for naming
                context_text = extract_text_context(page, image_bbox)
                
                # Generate filename
                if context_text:
                    base_name = sanitize_filename(context_text)
                else:
                    base_name = f"page_{page_num + 1}_img_{img_index + 1}"
                
                # Ensure unique filename
                filename = f"{base_name}.{image_ext}"
                counter = 1
                while (output_dir / filename).exists():
                    filename = f"{base_name}_{counter}.{image_ext}"
                    counter += 1
                
                output_path = output_dir / filename
                
                # Save the image
                with open(output_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                extracted_images.append({
                    "filename": filename,
                    "page": page_num + 1,
                    "size": len(image_bytes),
                    "context": context_text,
                    "path": str(output_path)
                })
                
                print(f"    ✓ Extracted: {filename} ({len(image_bytes)} bytes)")
                if context_text:
                    print(f"      Context: {context_text[:60]}...")
                
            except Exception as e:
                print(f"    ✗ Error extracting image {img_index + 1}: {e}")
                continue
    
    doc.close()
    return extracted_images


def process_pdf_directory(input_dir: str, output_base_dir: str = "extracted_images"):
    """
    Process all PDF files in a directory.
    """
    input_dir = Path(input_dir)
    output_base_dir = Path(output_base_dir)
    
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        return
    
    pdf_files = list(input_dir.glob("*.pdf")) + list(input_dir.glob("*.PDF"))
    
    if not pdf_files:
        print(f"No PDF files found in: {input_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    
    all_extracted = []
    for pdf_file in pdf_files:
        # Create output directory for this PDF
        pdf_output_dir = output_base_dir / pdf_file.stem
        images = extract_images_from_pdf(str(pdf_file), str(pdf_output_dir))
        all_extracted.extend(images)
    
    print(f"\n{'='*60}")
    print(f"Extraction complete!")
    print(f"Total images extracted: {len(all_extracted)}")
    print(f"Output directory: {output_base_dir}")
    print(f"{'='*60}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf_images.py <pdf_file_or_directory> [output_directory]")
        print("\nExample:")
        print("  python extract_pdf_images.py document.pdf")
        print("  python extract_pdf_images.py ./pdfs/ extracted_images/")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "extracted_images"
    
    if input_path.is_file() and input_path.suffix.lower() == '.pdf':
        # Process single PDF
        pdf_output_dir = Path(output_dir) / input_path.stem
        extract_images_from_pdf(str(input_path), str(pdf_output_dir))
    elif input_path.is_dir():
        # Process directory of PDFs
        process_pdf_directory(str(input_path), output_dir)
    else:
        print(f"Error: {input_path} is not a PDF file or directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
