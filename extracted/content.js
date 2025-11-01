// Content script for Moodle Gemini Search Extension
// Provides Ctrl+G functionality to get AI assistance on any page

console.log('🔵 Moodle Gemini Search content script loaded on:', window.location.href);
console.log('🔵 Extension is working - try Ctrl+G to test!');

// Wait a bit to ensure other extensions have loaded
setTimeout(() => {
  console.log('🔵 Moodle Gemini Search - Initializing after other extensions...');
  initializeGeminiSearch();
}, 100);

// Global variables
let isProcessingRequest = false;
let currentPopup = null;

// Helper function to escape HTML and prevent XSS attacks
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Function to display error message
function displayError(message) {
  console.error('🔴 Error:', message);
  
  // Remove existing popup if any
  if (currentPopup) {
    currentPopup.remove();
    currentPopup = null;
  }
  
  // Create error popup
  const popup = document.createElement('div');
  popup.id = 'gemini-search-popup';
  popup.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    width: 400px;
    max-height: 500px;
    background: #ff4444;
    color: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 10000;
    font-family: Arial, sans-serif;
    font-size: 14px;
    line-height: 1.4;
    border: 2px solid #ff6666;
  `;
  
  popup.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
      <strong>❌ Error</strong>
      <button id="close-error-btn" style="background: none; border: none; color: white; font-size: 18px; cursor: pointer;">×</button>
    </div>
    <div id="error-message"></div>
  `;
  
  // Safely insert error message using textContent to prevent XSS
  const errorDiv = popup.querySelector('#error-message');
  errorDiv.textContent = message;
  
  // Safely attach close button handler to avoid onclick injection
  const closeBtn = popup.querySelector('#close-error-btn');
  closeBtn.addEventListener('click', () => {
    popup.remove();
    currentPopup = null;
  });
  
  document.body.appendChild(popup);
  currentPopup = popup;
  
  // Auto-remove after 10 seconds
  setTimeout(() => {
    if (popup.parentNode) {
      popup.remove();
    }
  }, 10000);
}

// Function to display loading popup
function displayLoading() {
  // Remove existing popup if any
  if (currentPopup) {
    currentPopup.remove();
    currentPopup = null;
  }
  
  const popup = document.createElement('div');
  popup.id = 'gemini-search-popup';
  popup.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    width: 400px;
    background: #2196F3;
    color: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 10000;
    font-family: Arial, sans-serif;
    font-size: 14px;
    line-height: 1.4;
  `;
  
  popup.innerHTML = `
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
      <div style="width: 20px; height: 20px; border: 2px solid #fff; border-top: 2px solid transparent; border-radius: 50%; animation: spin 1s linear infinite; margin-right: 10px;"></div>
      <strong>🤖 Analyzing with Gemini...</strong>
    </div>
    <div>Processing page content and images...</div>
    <style>
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    </style>
  `;
  
  document.body.appendChild(popup);
  currentPopup = popup;
}

// Function to display AI response
function displayResponse(response, model) {
  // Remove existing popup if any
  if (currentPopup) {
    currentPopup.remove();
    currentPopup = null;
  }
  
  const popup = document.createElement('div');
  popup.id = 'gemini-search-popup';
  popup.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    width: 500px;
    max-height: 600px;
    background: #4CAF50;
    color: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 10000;
    font-family: Arial, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    overflow-y: auto;
    border: 2px solid #66BB6A;
  `;
  
  // Create safe HTML structure to prevent XSS attacks
  popup.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
      <div style="display: flex; align-items: center;">
        <span style="font-size: 20px; margin-right: 8px;">🤖</span>
        <strong>Gemini Response</strong>
        <span style="margin-left: 10px; font-size: 12px; opacity: 0.8;">(${escapeHtml(model)})</span>
      </div>
      <button id="close-popup-btn" style="background: none; border: none; color: white; font-size: 18px; cursor: pointer;">×</button>
    </div>
    <div id="response-content" style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 5px; white-space: pre-wrap;"></div>
    <div style="margin-top: 15px; font-size: 12px; opacity: 0.8; text-align: center;">
      Press Ctrl+G again to ask another question
    </div>
  `;
  
  // Safely insert response text using textContent to prevent XSS
  const responseDiv = popup.querySelector('#response-content');
  responseDiv.textContent = response;
  
  // Safely attach close button handler to avoid onclick injection
  const closeBtn = popup.querySelector('#close-popup-btn');
  closeBtn.addEventListener('click', () => {
    popup.remove();
    currentPopup = null;
  });
  
  document.body.appendChild(popup);
  currentPopup = popup;
  
  // Make popup draggable
  let isDragging = false;
  let startX, startY;
  
  const header = popup.querySelector('div');
  header.style.cursor = 'move';
  
  header.addEventListener('mousedown', (e) => {
    isDragging = true;
    startX = e.clientX - popup.offsetLeft;
    startY = e.clientY - popup.offsetTop;
    e.preventDefault();
  });
  
  document.addEventListener('mousemove', (e) => {
    if (isDragging) {
      popup.style.left = (e.clientX - startX) + 'px';
      popup.style.top = (e.clientY - startY) + 'px';
      popup.style.right = 'auto';
    }
  });
  
  document.addEventListener('mouseup', () => {
    isDragging = false;
  });
}

// Function to get page content
function getPageContent() {
  // Get selected text if any
  const selectedText = window.getSelection().toString().trim();
  
  if (selectedText) {
    console.log('Using selected text:', selectedText);
    return selectedText;
  }
  
  // Get page content
  const content = document.body.innerText || document.body.textContent || '';
  console.log('Using page content, length:', content.length);
  
  // Limit content length to avoid API limits
  if (content.length > 8000) {
    return content.substring(0, 8000) + '... [content truncated]';
  }
  
  return content;
}

// Function to get page images
async function getPageImages() {
  const images = [];
  const imgElements = document.querySelectorAll('img');
  
  for (const img of imgElements) {
    try {
      // Skip if image is too small or is a data URL
      if (img.width < 50 || img.height < 50 || img.src.startsWith('data:')) {
        continue;
      }
      
      // Skip cross-origin images that can't be processed
      if (img.crossOrigin && img.crossOrigin !== 'anonymous') {
        continue;
      }
      
      // Convert image to base64
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      canvas.width = Math.min(img.width, 800);
      canvas.height = Math.min(img.height, 600);
      
      // DON'T modify the original image - this causes it to reload and disappear
      // Instead, we'll skip cross-origin images that can't be processed
      
      // Check if image is loaded and not broken
      if (img.complete && img.naturalWidth > 0) {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const dataURL = canvas.toDataURL('image/jpeg', 0.8);
        
        images.push({
          data: dataURL.split(',')[1],
          mimeType: 'image/jpeg'
        });
      } else {
        // Skip broken images
        continue;
      }
      
      // Limit to 3 images to avoid API limits
      if (images.length >= 3) break;
    } catch (error) {
      console.warn('Error processing image:', error);
      // Continue with other images even if one fails
      continue;
    }
  }
  
  return images;
}

// Main function to handle AI request
async function handleAIRequest() {
  console.log('=== handleAIRequest CALLED ===');
  
  // Prevent duplicate requests
  if (isProcessingRequest) {
    console.log('Request already in progress, ignoring duplicate');
    return;
  }
  
  isProcessingRequest = true;
  
  try {
    // Show loading popup
    displayLoading();
    
    // Get page content and images
    const content = getPageContent();
    const images = await getPageImages();
    
    console.log('Content length:', content.length);
    console.log('Images found:', images.length);
    
    // Check if extension context is still valid
    if (!chrome.runtime || !chrome.runtime.sendMessage) {
      displayError('Extension context invalidated. Please reload the page.');
      return;
    }
    
    // Send to background script with error handling
    let response;
    try {
      response = await chrome.runtime.sendMessage({
        type: 'ANALYZE_CONTENT',
        data: {
          content: content,
          images: images,
          pageUrl: window.location.href
        }
      });
    } catch (error) {
      if (error.message && error.message.includes('Extension context invalidated')) {
        displayError('Extension context invalidated. Please reload the page and try again.');
        return;
      } else {
        displayError('Failed to communicate with extension: ' + error.message);
        return;
      }
    }
    
    if (response.error) {
      // Debug: Log the exact error structure
      console.log('🔍 DEBUG: response.error type:', typeof response.error);
      console.log('🔍 DEBUG: response.error value:', response.error);
      
      // Handle different error formats
      let errorMessage = 'Unknown error occurred';
      if (typeof response.error === 'string') {
        errorMessage = response.error;
      } else if (response.error && typeof response.error === 'object') {
        if (response.error.message) {
          errorMessage = response.error.message;
        } else if (response.error.error && response.error.error.message) {
          errorMessage = response.error.error.message;
        } else {
          errorMessage = JSON.stringify(response.error);
        }
      }
      displayError(errorMessage);
    } else if (response.success) {
      displayResponse(response.response, response.model);
    } else {
      displayError('Unknown error occurred');
    }
    
  } catch (error) {
    console.error('Error in handleAIRequest:', error);
    displayError('Failed to process request: ' + error.message);
  } finally {
    isProcessingRequest = false;
  }
}

// Function to initialize Gemini Search functionality
function initializeGeminiSearch() {
  console.log('🔵 Initializing Gemini Search event listeners...');
  
  // Single efficient Ctrl+G handler (capture phase to intercept before Chrome)
  // Fixed: Removed 11 redundant duplicate event listeners that were causing performance issues
  async function handleCtrlG(e) {
    // Check if Ctrl+G is pressed (case-insensitive)
    if (e.ctrlKey && !e.shiftKey && (e.key === 'G' || e.key === 'g')) {
      console.log('🔵 Ctrl+G detected - preventing default');
      
      // Prevent default browser behavior and stop propagation
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      e.returnValue = false;
      
      // Handle the AI request
      console.log('🔵 Calling handleAIRequest');
      try {
        await handleAIRequest();
      } catch (error) {
        console.error('🔴 Error in handleAIRequest:', error);
        displayError('Error processing request: ' + error.message);
      }
      
      return false;
    }
  }
  
  // Add single capture-phase listener on document (most efficient approach)
  // Using capture phase (true) ensures we intercept before Chrome's default handlers
  document.addEventListener('keydown', handleCtrlG, true);
  
  // Also add listener on window as fallback for some edge cases
  // (but only call handleAIRequest from one listener to avoid duplicates)
  window.addEventListener('keydown', (e) => {
    if (e.ctrlKey && !e.shiftKey && (e.key === 'G' || e.key === 'g')) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      // Don't call handleAIRequest here - document listener already handles it
      return false;
    }
  }, true);
  
  console.log('🔵 Gemini Search event listeners initialized successfully!');
}

console.log('Moodle Gemini Search content script initialized');
