# Key Features & Code Highlights

## 🎯 Problem #1: Full-Page Scans

### What Was Happening
Your previous script was exporting entire scanned pages as "images" because scanned PDFs store each page as a bitmap image with no text layer.

### The Fix
```python
def is_full_page_scan(self, img_bbox: Tuple, page_bbox: Tuple) -> bool:
    """Determine if an image is likely a full-page scan."""
    img_width = img_bbox[2] - img_bbox[0]
    img_height = img_bbox[3] - img_bbox[1]
    page_width = page_bbox[2] - page_bbox[0]
    page_height = page_bbox[3] - page_bbox[1]
    
    img_area = img_width * img_height
    page_area = page_width * page_height
    
    coverage = img_area / page_area
    
    # If image covers more than 85% of page, it's likely a scan
    return coverage > self.max_page_coverage
```

### Why It Works
- Calculates what percentage of the page each image covers
- Default threshold: 85% (adjustable)
- If an image is basically the whole page → it's a scan, not a figure

### Usage
```bash
# Default (85% threshold)
python extract_pdf_images.py document.pdf

# More aggressive (70% threshold)
python extract_pdf_images.py document.pdf --max-coverage 0.7

# Less aggressive (95% threshold)
python extract_pdf_images.py document.pdf --max-coverage 0.95
```

---

## 📝 Problem #2: Poor Contextual Naming

### What Was Happening
Previous script couldn't extract meaningful text from around images to generate descriptive filenames.

### The Fix: Multi-Region Text Extraction
```python
def extract_text_context(self, page, img_bbox: Tuple) -> str:
    """Extract text near the image for contextual naming."""
    contexts = []
    
    # Text ABOVE image (100px above)
    above_rect = fitz.Rect(
        img_bbox[0],
        max(0, img_bbox[1] - 100),
        img_bbox[2],
        img_bbox[1]
    )
    
    # Text BELOW image (100px below)
    below_rect = fitz.Rect(
        img_bbox[0],
        img_bbox[3],
        img_bbox[2],
        min(page.rect.height, img_bbox[3] + 100)
    )
    
    # Text to the LEFT (150px left)
    # Text to the RIGHT (150px right)
    # ... (similar code)
    
    # Extract from all regions
    for rect in [above_rect, below_rect, left_rect, right_rect]:
        text = page.get_text("text", clip=rect).strip()
        if text:
            contexts.append(text)
    
    return " ".join(contexts)[:self.context_chars]
```

### Why It Works
- Looks in 4 directions around the image
- Captures captions, titles, and nearby text
- Combines all context into one string
- Limits to configurable character count (default: 200)

---

## 🔤 Problem #3: Filename Generation

### What Was Happening
Filenames weren't descriptive of image content.

### The Fix: Multi-Strategy Naming
```python
def generate_filename(self, context, page_num, img_index, pdf_name):
    """Generate a meaningful filename based on context."""
    
    # STRATEGY 1: Look for figure/table references
    fig_pattern = r'(?i)(figure|fig|table|chart|diagram|illustration)\s*(\d+\.?\d*)'
    fig_match = re.search(fig_pattern, context)
    
    if fig_match:
        prefix = fig_match.group(1).lower()  # "figure", "table"
        number = fig_match.group(2).replace('.', '_')  # "3.2" → "3_2"
        base_name = f"{prefix}_{number}"
        # Result: "figure_3_2_p5_i1.png"
    
    # STRATEGY 2: Extract meaningful keywords
    else:
        meaningful_words = []
        for word in words[:15]:
            clean_word = re.sub(r'[^\w]', '', word)
            # Keep if: Capitalized, >3 chars, not common word
            if (clean_word and 
                len(clean_word) > 3 and
                clean_word[0].isupper() and
                clean_word.lower() not in ['the', 'this', 'that', ...]):
                meaningful_words.append(clean_word)
        
        base_name = "_".join(meaningful_words[:5])
        # Result: "Neural_Network_Architecture_Overview_p5_i1.png"
    
    # STRATEGY 3: Fallback
    if not base_name:
        base_name = f"{pdf_name}_page{page_num}"
        # Result: "DocumentName_page5_p5_i1.png"
    
    return f"{base_name}_p{page_num}_i{img_index}"
```

### Naming Examples

**Input Context**: "Figure 3.2: Neural network architecture showing the flow..."
**Output**: `figure_3_2_p5_i1.png`

**Input Context**: "Table 1: Comparison of Results across Different Methods"
**Output**: `table_1_Comparison_Results_Different_Methods_p8_i1.jpg`

**Input Context**: "The following diagram illustrates the system architecture..."
**Output**: `diagram_System_Architecture_p12_i2.png`

**Input Context**: "" (no text - scanned PDF)
**Output**: `DocumentName_page5_p5_i1.png`

---

## 🎨 Problem #4: Extracting Images vs Text

### What's Different
```python
# ❌ WRONG: Rendering page as image (includes text)
page_image = page.get_pixmap()  # Don't do this

# ✅ RIGHT: Extract embedded images only
image_list = page.get_images()
for img_info in image_list:
    xref = img_info[0]
    base_image = doc.extract_image(xref)  # Pure image data
    image_bytes = base_image["image"]     # No text!
```

### Key Point
- Text stays as text in the PDF
- Only actual embedded images are extracted
- Surrounding text is read separately for naming
- **Text is never included in the image files**

---

## ⚙️ Configuration Options

### All Thresholds Are Adjustable

```python
class PDFImageExtractor:
    def __init__(self, 
                 output_dir: str = "extracted_images",
                 min_width: int = 100,           # ← Adjustable
                 min_height: int = 100,          # ← Adjustable
                 max_page_coverage: float = 0.85, # ← Adjustable
                 context_chars: int = 200):      # ← Adjustable
```

### Via Command Line
```bash
python extract_pdf_images.py document.pdf \
  --min-width 150 \
  --min-height 150 \
  --max-coverage 0.9 \
  --context-chars 300 \
  -o my_images
```

---

## 📊 Progress Reporting

### Detailed Output
```
Processing: research_paper.pdf

  Page 1: Found 2 image(s)
    Image 1: Skipped (too small: 50x50)
    Image 2: Skipped (full-page scan)
  
  Page 3: Found 1 image(s)
    Image 1: ✓ Saved as figure_1_Neural_Network_p3_i1.png
      Context: Figure 1. Neural network architecture showing...
      Size: 800x600
  
  Page 5: Found 2 image(s)
    Image 1: ✓ Saved as table_2_Results_p5_i1.jpg
      Context: Table 2. Comparison of results across...
      Size: 1200x400
    Image 2: ✓ Saved as Algorithm_Flowchart_p5_i2.png
      Context: Algorithm 1 Flowchart depicting the process...
      Size: 600x800
  
  Summary: 3 extracted, 2 skipped

==================================================
Processing complete!
Total images extracted: 3
Total images skipped: 2
Output location: /path/to/extracted_images
==================================================
```

---

## 🚀 Performance Features

### Memory Efficient
```python
# Processes one page at a time
for page_num in range(len(doc)):
    page = doc[page_num]
    # ... process page ...
    # Page data is freed when moving to next page
```

### Error Handling
```python
try:
    # Extract image
    base_image = doc.extract_image(xref)
    # ... process ...
except Exception as e:
    # Don't crash entire script if one image fails
    print(f"Error: {str(e)}")
    continue  # Move to next image
```

### Duplicate Prevention
```python
output_path = pdf_output_dir / f"{filename}.{ext}"

# Auto-increment if file exists
counter = 1
while output_path.exists():
    output_path = pdf_output_dir / f"{filename}_{counter}.{ext}"
    counter += 1
```

---

## 🎯 Summary of Improvements

| Feature | Implementation | Benefit |
|---------|---------------|---------|
| **Scan Detection** | Coverage ratio calculation | No more full-page scans |
| **Size Filtering** | Min width/height check | No more tiny logos |
| **Context Extraction** | 4-direction spatial text | Better filename context |
| **Smart Naming** | Regex + keyword extraction | Meaningful filenames |
| **Pure Images** | Extract embedded images only | No text in images |
| **Organization** | Per-document directories | Easy navigation |
| **Reporting** | Detailed progress output | Know what's happening |
| **Error Handling** | Try-catch per image | Don't crash on errors |
| **Configurability** | All thresholds adjustable | Works for any content |

---

## 🔧 Quick Tweaking Guide

### Too many images being skipped?
```bash
# Lower the minimum size
python extract_pdf_images.py doc.pdf --min-width 50 --min-height 50
```

### Still getting full-page scans?
```bash
# Lower the coverage threshold
python extract_pdf_images.py doc.pdf --max-coverage 0.7
```

### Filenames not descriptive enough?
```bash
# Increase context extraction
python extract_pdf_images.py doc.pdf --context-chars 400
```

### Too much output?
```bash
# Use quiet mode
python extract_pdf_images.py doc.pdf -q
```

---

## 📖 Next Steps

1. **Install**: `pip install -r requirements.txt`
2. **Test**: `python extract_pdf_images.py sample.pdf`
3. **Adjust**: Fine-tune thresholds for your content
4. **Run**: Process your entire library
5. **Review**: Check if results meet expectations

**Full docs**: See `PDF_IMAGE_EXTRACTOR_README.md` and `IMPROVEMENTS_SUMMARY.md`
