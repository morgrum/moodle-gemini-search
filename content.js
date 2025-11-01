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
let apiKeyPromptVisible = false;
let apiKeyPromptElement = null;

// Promise wrapper for chrome.runtime.sendMessage for broader browser support
function sendRuntimeMessage(message) {
  return new Promise((resolve, reject) => {
    if (!chrome.runtime || typeof chrome.runtime.sendMessage !== 'function') {
      reject(new Error('Extension messaging is unavailable.'));
      return;
    }

    try {
      chrome.runtime.sendMessage(message, (response) => {
        const lastError = chrome.runtime.lastError;
        if (lastError) {
          reject(new Error(lastError.message));
          return;
        }
        resolve(response);
      });
    } catch (error) {
      reject(error);
    }
  });
}

function removeApiKeyPrompt() {
  if (apiKeyPromptElement && apiKeyPromptElement.parentNode) {
    apiKeyPromptElement.parentNode.removeChild(apiKeyPromptElement);
  }
  apiKeyPromptElement = null;
  apiKeyPromptVisible = false;
}

function showApiKeyPrompt() {
  if (apiKeyPromptVisible) {
    return;
  }
  apiKeyPromptVisible = true;

  const overlay = document.createElement('div');
  overlay.id = 'gemini-api-key-overlay';
  overlay.style.cssText = `
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.65);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10001;
    font-family: Arial, sans-serif;
  `;

  const dialog = document.createElement('div');
  dialog.style.cssText = `
    background: #ffffff;
    color: #1f2933;
    width: min(420px, 90%);
    border-radius: 12px;
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.35);
    padding: 24px;
  `;

  const title = document.createElement('h3');
  title.textContent = 'Add Your Gemini API Key';
  title.style.cssText = 'margin: 0 0 12px; font-size: 20px;';

  const description = document.createElement('p');
  description.textContent = 'For security, the extension needs your personal Gemini API key. Paste it below and click Save to continue.';
  description.style.cssText = 'margin: 0 0 16px; line-height: 1.5;';

  const input = document.createElement('input');
  input.type = 'password';
  input.autocomplete = 'off';
  input.style.cssText = `
    width: 100%;
    box-sizing: border-box;
    padding: 10px 12px;
    border-radius: 6px;
    border: 1px solid #d1d5db;
    font-size: 14px;
    margin-bottom: 12px;
  `;
  input.placeholder = 'AIza...';

  const status = document.createElement('div');
  status.className = 'gemini-api-key-status';
  status.style.cssText = 'min-height: 18px; font-size: 12px; color: #dc2626; margin-bottom: 12px;';

  const buttonRow = document.createElement('div');
  buttonRow.style.cssText = 'display: flex; justify-content: flex-end; gap: 8px;';

  const cancelButton = document.createElement('button');
  cancelButton.textContent = 'Cancel';
  cancelButton.type = 'button';
  cancelButton.style.cssText = `
    background: #e5e7eb;
    border: none;
    color: #111827;
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
  `;

  const saveButton = document.createElement('button');
  saveButton.textContent = 'Save';
  saveButton.type = 'button';
  saveButton.style.cssText = `
    background: #2563eb;
    border: none;
    color: white;
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
  `;

  cancelButton.addEventListener('click', () => {
    removeApiKeyPrompt();
  });

  saveButton.addEventListener('click', async () => {
    const apiKey = (input.value || '').trim();
    status.style.color = '#dc2626';

    if (!apiKey) {
      status.textContent = 'Please enter a valid API key before saving.';
      input.focus();
      return;
    }

    saveButton.disabled = true;
    cancelButton.disabled = true;
    status.style.color = '#2563eb';
    status.textContent = 'Saving API key...';

    try {
      const result = await sendRuntimeMessage({ type: 'SAVE_API_KEY', apiKey });
      if (!result || !result.success) {
        const errorMessage = result && result.error ? result.error : 'Unable to save the API key.';
        status.style.color = '#dc2626';
        status.textContent = errorMessage;
        return;
      }

      status.style.color = '#16a34a';
      status.textContent = 'API key saved. You can trigger Ctrl+G again.';
      input.value = '';

      setTimeout(() => {
        removeApiKeyPrompt();
        if (!isProcessingRequest) {
          handleAIRequest();
        }
      }, 600);
    } catch (error) {
      status.style.color = '#dc2626';
      status.textContent = error.message || 'Failed to save the API key.';
    } finally {
      saveButton.disabled = false;
      cancelButton.disabled = false;
    }
  });

  buttonRow.appendChild(cancelButton);
  buttonRow.appendChild(saveButton);

  dialog.appendChild(title);
  dialog.appendChild(description);
  dialog.appendChild(input);
  dialog.appendChild(status);
  dialog.appendChild(buttonRow);

  overlay.appendChild(dialog);
  document.body.appendChild(overlay);

  apiKeyPromptElement = overlay;
  input.focus();
}

// Function to display error message
function displayError(message) {
  console.error('🔴 Error:', message);
  
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
  `;

  const header = document.createElement('div');
  header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;';

  const title = document.createElement('strong');
  title.textContent = '❌ Error';

  const closeButton = document.createElement('button');
  closeButton.type = 'button';
  closeButton.textContent = '×';
  closeButton.style.cssText = 'background: none; border: none; color: white; font-size: 18px; cursor: pointer;';
  closeButton.addEventListener('click', () => {
    popup.remove();
    if (currentPopup === popup) {
      currentPopup = null;
    }
  });

  header.appendChild(title);
  header.appendChild(closeButton);

  const messageContainer = document.createElement('div');
  messageContainer.textContent = message;

  popup.appendChild(header);
  popup.appendChild(messageContainer);

  document.body.appendChild(popup);
  currentPopup = popup;

  setTimeout(() => {
    if (popup.parentNode) {
      popup.remove();
      if (currentPopup === popup) {
        currentPopup = null;
      }
    }
  }, 10000);

  if (typeof message === 'string' && /API key/i.test(message)) {
    showApiKeyPrompt();
  }
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

  const header = document.createElement('div');
  header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; cursor: move;';

  const titleWrapper = document.createElement('div');
  titleWrapper.style.cssText = 'display: flex; align-items: center; gap: 8px;';

  const icon = document.createElement('span');
  icon.textContent = '🤖';
  icon.style.cssText = 'font-size: 20px;';

  const title = document.createElement('strong');
  title.textContent = 'Gemini Response';

  const modelLabel = document.createElement('span');
  modelLabel.textContent = `(${model})`;
  modelLabel.style.cssText = 'font-size: 12px; opacity: 0.8;';

  titleWrapper.appendChild(icon);
  titleWrapper.appendChild(title);
  titleWrapper.appendChild(modelLabel);

  const closeButton = document.createElement('button');
  closeButton.type = 'button';
  closeButton.textContent = '×';
  closeButton.style.cssText = 'background: none; border: none; color: white; font-size: 18px; cursor: pointer;';
  closeButton.addEventListener('click', () => {
    popup.remove();
    if (currentPopup === popup) {
      currentPopup = null;
    }
  });

  header.appendChild(titleWrapper);
  header.appendChild(closeButton);

  const responseContainer = document.createElement('div');
  responseContainer.style.cssText = 'background: rgba(255,255,255,0.1); padding: 15px; border-radius: 5px; white-space: pre-wrap;';
  responseContainer.textContent = response;

  const footer = document.createElement('div');
  footer.style.cssText = 'margin-top: 15px; font-size: 12px; opacity: 0.8; text-align: center;';
  footer.textContent = 'Press Ctrl+G again to ask another question';

  popup.appendChild(header);
  popup.appendChild(responseContainer);
  popup.appendChild(footer);

  document.body.appendChild(popup);
  currentPopup = popup;

  let isDragging = false;
  let startX = 0;
  let startY = 0;

  const onMouseMove = (e) => {
    if (!isDragging) return;
    popup.style.left = `${e.clientX - startX}px`;
    popup.style.top = `${e.clientY - startY}px`;
    popup.style.right = 'auto';
  };

  const onMouseUp = () => {
    isDragging = false;
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  };

  header.addEventListener('mousedown', (e) => {
    isDragging = true;
    startX = e.clientX - popup.offsetLeft;
    startY = e.clientY - popup.offsetTop;
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    e.preventDefault();
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
      response = await sendRuntimeMessage({
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
      }
      displayError('Failed to communicate with extension: ' + error.message);
      return;
    }

    if (!response) {
      displayError('No response received from the extension service.');
      return;
    }

    if (response.error) {
      console.log('🔍 DEBUG: response.error type:', typeof response.error);
      console.log('🔍 DEBUG: response.error value:', response.error);

      let errorMessage = 'Unknown error occurred';
      if (typeof response.error === 'string') {
        errorMessage = response.error;
      } else if (response.error && typeof response.error === 'object') {
        if (response.error.message) {
          errorMessage = response.error.message;
        } else if (response.error.error && response.error.error.message) {
          errorMessage = response.error.error.message;
        } else {
          try {
            errorMessage = JSON.stringify(response.error);
          } catch (serializationError) {
            errorMessage = 'An unknown error occurred while processing the response.';
          }
        }
      }

      displayError(errorMessage);
      return;
    }

    if (response.success) {
      displayResponse(response.response, response.model);
      return;
    }

    displayError('Unknown error occurred.');
    
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
