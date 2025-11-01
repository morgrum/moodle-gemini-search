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

// Function to display error message
function displayError(message) {
  console.error('🔴 Error:', message);

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
    display: flex;
    flex-direction: column;
    gap: 10px;
  `;

  const header = document.createElement('div');
  header.style.cssText = 'display: flex; justify-content: space-between; align-items: center;';

  const title = document.createElement('strong');
  title.textContent = '❌ Error';
  header.appendChild(title);

  const closeButton = document.createElement('button');
  closeButton.type = 'button';
  closeButton.textContent = '×';
  closeButton.setAttribute('aria-label', 'Close error');
  closeButton.style.cssText = 'background: none; border: none; color: white; font-size: 18px; cursor: pointer; line-height: 1;';
  closeButton.addEventListener('click', () => {
    if (popup.parentNode) {
      popup.remove();
    }
    if (currentPopup === popup) {
      currentPopup = null;
    }
  });
  header.appendChild(closeButton);

  const messageContainer = document.createElement('div');
  messageContainer.textContent = typeof message === 'string' ? message : String(message);

  popup.appendChild(header);
  popup.appendChild(messageContainer);

  document.body.appendChild(popup);
  currentPopup = popup;

  // Auto-remove after 10 seconds
  setTimeout(() => {
    if (popup.parentNode) {
      popup.remove();
    }
    if (currentPopup === popup) {
      currentPopup = null;
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
    display: flex;
    flex-direction: column;
    gap: 15px;
  `;

  const header = document.createElement('div');
  header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; cursor: move; gap: 10px;';

  const headerLeft = document.createElement('div');
  headerLeft.style.cssText = 'display: flex; align-items: center; gap: 8px;';

  const icon = document.createElement('span');
  icon.textContent = '🤖';
  icon.style.fontSize = '20px';
  headerLeft.appendChild(icon);

  const title = document.createElement('strong');
  title.textContent = 'Gemini Response';
  headerLeft.appendChild(title);

  const modelTag = document.createElement('span');
  modelTag.textContent = `(${model})`;
  modelTag.style.cssText = 'margin-left: 6px; font-size: 12px; opacity: 0.8;';
  headerLeft.appendChild(modelTag);

  header.appendChild(headerLeft);

  const closeButton = document.createElement('button');
  closeButton.type = 'button';
  closeButton.textContent = '×';
  closeButton.setAttribute('aria-label', 'Close Gemini response');
  closeButton.style.cssText = 'background: none; border: none; color: white; font-size: 18px; cursor: pointer; line-height: 1;';
  closeButton.addEventListener('mousedown', (event) => event.stopPropagation());
  closeButton.addEventListener('click', () => {
    if (popup.parentNode) {
      popup.remove();
    }
    if (currentPopup === popup) {
      currentPopup = null;
    }
  });
  header.appendChild(closeButton);

  const responseContainer = document.createElement('div');
  responseContainer.style.cssText = 'background: rgba(255,255,255,0.1); padding: 15px; border-radius: 5px; white-space: pre-wrap; word-break: break-word;';
  if (typeof response === 'string') {
    responseContainer.textContent = response;
  } else {
    responseContainer.textContent = JSON.stringify(response, null, 2);
  }

  const instructions = document.createElement('div');
  instructions.style.cssText = 'font-size: 12px; opacity: 0.8; text-align: center;';
  instructions.textContent = 'Press Ctrl+G again to ask another question';

  popup.appendChild(header);
  popup.appendChild(responseContainer);
  popup.appendChild(instructions);

  document.body.appendChild(popup);
  currentPopup = popup;

  let isDragging = false;
  let startX = 0;
  let startY = 0;

  header.addEventListener('mousedown', (e) => {
    isDragging = true;
    startX = e.clientX - popup.offsetLeft;
    startY = e.clientY - popup.offsetTop;
    e.preventDefault();
  });

  const onMouseMove = (e) => {
    if (!isDragging) return;
    popup.style.left = `${e.clientX - startX}px`;
    popup.style.top = `${e.clientY - startY}px`;
    popup.style.right = 'auto';
  };

  const onMouseUp = () => {
    isDragging = false;
  };

  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseup', onMouseUp);

  // Ensure listeners are cleaned up when popup is removed
  const observer = new MutationObserver(() => {
    if (!document.body.contains(popup)) {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      observer.disconnect();
    }
  });
  observer.observe(document.body, { childList: true });
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
      
      const naturalWidth = img.naturalWidth || img.width;
      const naturalHeight = img.naturalHeight || img.height;

      if (!naturalWidth || !naturalHeight) {
        continue;
      }

      // Convert image to base64 while maintaining aspect ratio
      const maxWidth = 800;
      const maxHeight = 600;
      const widthRatio = maxWidth / naturalWidth;
      const heightRatio = maxHeight / naturalHeight;
      const scale = Math.min(1, widthRatio, heightRatio);

      const targetWidth = Math.max(1, Math.round(naturalWidth * scale));
      const targetHeight = Math.max(1, Math.round(naturalHeight * scale));

      const canvas = document.createElement('canvas');
      canvas.width = targetWidth;
      canvas.height = targetHeight;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        continue;
      }
      
      // DON'T modify the original image - this causes it to reload and disappear
      // Instead, we'll skip cross-origin images that can't be processed
      
      // Check if image is loaded and not broken
      if (img.complete && img.naturalWidth > 0) {
        ctx.drawImage(img, 0, 0, targetWidth, targetHeight);
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

// Ensure an API key is available in storage, prompting the user if needed
async function ensureApiKey() {
  try {
    const stored = await chrome.storage.sync.get({ apiKey: '' });
    const existingKey = typeof stored.apiKey === 'string' ? stored.apiKey.trim() : '';
    if (existingKey) {
      return existingKey;
    }
  } catch (error) {
    console.warn('Unable to read stored API key:', error);
  }

  const userInput = window.prompt('Enter your Gemini API key to use Moodle Gemini Search:');
  if (!userInput) {
    throw new Error('Gemini API key entry cancelled. The request was not sent.');
  }

  const cleanedKey = userInput.trim();
  if (!cleanedKey) {
    throw new Error('Gemini API key cannot be empty.');
  }

  try {
    await chrome.storage.sync.set({ apiKey: cleanedKey });
  } catch (error) {
    console.error('Failed to save Gemini API key:', error);
    throw new Error('Failed to save API key. Please try again.');
  }

  return cleanedKey;
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
    try {
      await ensureApiKey();
    } catch (keyError) {
      displayError(keyError.message);
      return;
    }

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
  
  // Universal Ctrl+G listener (capture phase to intercept before Chrome)
  document.addEventListener('keydown', async (e) => {
    console.log('🔵 Key pressed:', e.key, 'Ctrl:', e.ctrlKey, 'Shift:', e.shiftKey);
    
    if (e.ctrlKey && !e.shiftKey && (e.key === 'G' || e.key === 'g')) {
      console.log('🔵 Ctrl+G detected - preventing default IMMEDIATELY');
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      
      console.log('🔵 Calling handleAIRequest');
      try {
        await handleAIRequest();
      } catch (error) {
        console.error('🔴 Error in handleAIRequest:', error);
        displayError('Error processing request: ' + error.message);
      }
      return false;
    }
  }, true); // TRUE = capture phase (intercept before Chrome handlers)

  // Also add a more aggressive keydown listener
  window.addEventListener('keydown', async (e) => {
    if (e.ctrlKey && !e.shiftKey && (e.key === 'G' || e.key === 'g')) {
      console.log('🔵 Window Ctrl+G detected - preventing default');
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      
      console.log('🔵 Calling handleAIRequest from window listener');
      try {
        await handleAIRequest();
      } catch (error) {
        console.error('🔴 Error in handleAIRequest from window:', error);
        displayError('Error processing request: ' + error.message);
      }
      return false;
    }
  }, true);

  // Additional aggressive blocking for Chrome's search functionality
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && !e.shiftKey && (e.key === 'G' || e.key === 'g')) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      return false;
    }
  }, true);

  // Block keyup events as well
  document.addEventListener('keyup', (e) => {
    if (e.ctrlKey && !e.shiftKey && (e.key === 'G' || e.key === 'g')) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      return false;
    }
  }, true);

  // Override Chrome's default keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && !e.shiftKey && (e.key === 'G' || e.key === 'g')) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      return false;
    }
  }, true);

  // Block the specific Chrome search shortcut
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && !e.shiftKey && e.key === 'G') {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      return false;
    }
  }, true);

  // Override document-level keyboard handling
  document.onkeydown = function(e) {
    if (e.ctrlKey && !e.shiftKey && (e.key === 'G' || e.key === 'g')) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      return false;
    }
  };

  // Override window-level keyboard handling
  window.onkeydown = function(e) {
    if (e.ctrlKey && !e.shiftKey && (e.key === 'G' || e.key === 'g')) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      return false;
    }
  };

  // Block Chrome's default search behavior more aggressively
  document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && !e.shiftKey && (e.key === 'G' || e.key === 'g')) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      e.returnValue = false;
      return false;
    }
  }, true);

  // Additional blocking for Chrome's search dialog
  document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && !e.shiftKey && e.key === 'G') {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      e.returnValue = false;
      return false;
    }
  }, true);
  
  console.log('🔵 Gemini Search event listeners initialized successfully!');
}

console.log('Moodle Gemini Search content script initialized');
