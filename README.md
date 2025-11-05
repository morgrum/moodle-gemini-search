# Moodle Gemini Search Extension

A dedicated Chrome extension that provides instant AI assistance using Google's Gemini API. Press **Ctrl+G** anywhere to get intelligent responses about the current page content.

## Features

- **🔍 Instant AI Search**: Press Ctrl+G anywhere to get AI assistance
- **📄 Page Content Analysis**: Automatically scans and analyzes page content
- **🖼️ Image Processing**: Includes images in analysis when available
- **📝 Text Selection**: Select specific text and press Ctrl+G for targeted analysis
- **🎯 Smart Responses**: Uses Gemini 1.5 Flash and Pro models for intelligent responses
- **⚡ Fast & Reliable**: Embedded API key for immediate use

## Installation

### Method 1: Load Unpacked Extension (Recommended)

1. **Download** the extension files
2. **Extract** the ZIP file to a folder
3. **Open Chrome** → Go to `chrome://extensions/`
4. **Enable "Developer mode"** (toggle in top right)
5. **Click "Load unpacked"** → Select the extracted folder
6. **Test** by pressing Ctrl+G on any webpage

### Method 2: Install from GitHub

1. **Download** from: `https://github.com/morgrum/moodle-gemini-search/archive/main.zip`
2. **Extract** the ZIP file
3. **Follow Method 1** steps 3-6

## Usage

### Basic Usage
1. **Navigate** to any webpage
2. **Press Ctrl+G** to analyze the entire page
3. **View** the AI response in the popup

### Advanced Usage
1. **Select specific text** on the page
2. **Press Ctrl+G** to analyze only the selected text
3. **Get targeted** AI responses about your selection

### Features
- **Draggable Popup**: Click and drag the response popup to move it
- **Auto-close**: Popup automatically closes after 10 seconds (errors)
- **Model Selection**: Automatically uses the best available Gemini model
- **Usage Tracking**: Tracks daily API usage to stay within limits

## Supported Sites

- **Moodle Sites**: `moodle.abtech.edu` and related domains
- **Local Files**: HTML files opened in Chrome
- **Any Website**: Works on any webpage for general AI assistance

## API Information

- **Embedded API Key**: Included for immediate use
- **Models Used**: Gemini 1.5 Flash (250/day) and Gemini 1.5 Pro (50/day)
- **Usage Limits**: Automatically managed to stay within API limits
- **Fallback**: Switches between models when limits are reached

## Troubleshooting

### Extension Not Working
1. **Check Console**: Open Developer Tools (F12) and look for error messages
2. **Reload Extension**: Go to `chrome://extensions/` and click the reload button
3. **Check Permissions**: Ensure the extension has access to the current site

### Ctrl+G Not Working
1. **Try Different Sites**: Some sites may block keyboard shortcuts
2. **Check for Conflicts**: Other extensions might interfere
3. **Restart Chrome**: Close and reopen Chrome to refresh extensions

### API Errors
1. **Daily Limit Reached**: Wait until tomorrow for limits to reset
2. **Network Issues**: Check your internet connection
3. **API Key Issues**: The embedded key should work automatically

## Technical Details

- **Manifest Version**: 3 (latest Chrome extension standard)
- **Content Scripts**: Runs on document_start for early initialization
- **Background Script**: Service worker for API communication
- **Permissions**: storage, activeTab, tabs
- **API Endpoint**: Google Generative Language API

## Development

### File Structure
```
Moodle Gemini Search Extension/
├── manifest.json          # Extension configuration
├── content.js            # Main content script with Ctrl+G logic
├── background.js         # Background service worker with API calls
├── icon16.png           # 16x16 extension icon
├── icon48.png           # 48x48 extension icon
├── icon128.png          # 128x128 extension icon
└── README.md            # This file
```

### Key Features
- **Capture Phase Listeners**: Intercepts Ctrl+G before Chrome's default behavior
- **Image Processing**: Converts images to base64 for API analysis
- **Content Truncation**: Limits content to 8000 characters to avoid API limits
- **Error Handling**: Comprehensive error handling with user-friendly messages

## License

This extension is provided as-is for educational and personal use.

## Support

For issues or questions:
1. Check the browser console for error messages
2. Ensure you have a stable internet connection
3. Try reloading the extension in `chrome://extensions/`

---

**Note**: This extension uses Google's Gemini API with an embedded API key. Usage is subject to Google's API terms and rate limits.

---

## Figure Extraction Utility

Alongside the Chrome extension, this repository now includes a standalone helper
script for harvesting meaningful figures from large PDF collections.

### Features

- **Context-aware naming**: Saves each exported image using text found near the
  figure (captions, references, headings) rather than dumping raw page numbers.
- **Full-page scan filtering**: Skips pages that are just single bitmap scans to
  avoid noise in the output.
- **Vector drawing capture**: Renders chart- or diagram-like vector drawings in
  addition to embedded raster images.

### Requirements

```bash
pip install pymupdf
```

### Usage

```bash
python extract_pdf_figures.py --input /path/to/pdf_or_folder --output ./figures
```

Key options:

- `--context-words`: maximum number of nearby words to include in the filename
  (default: 20).
- `--context-margin`: how far from the figure (in PDF points) to look for
  naming context (default: 48).
- `--full-page-ratio`: skip images occupying more than this fraction of a page
  (default: 0.9).
- `--min-area-ratio`: ignore very small graphics (default: 0.01).

Each PDF gets its own folder under the chosen output directory. Figures are
saved in PNG format with filenames like
`report_p003_img01_figure-2-process-overview.png`.
