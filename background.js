// Background service worker for Moodle Gemini Search Extension

// API key should be provided by the user for security reasons
// Users can get their API key from https://makersuite.google.com/app/apikey
const DEFAULT_API_KEY = null; // No default API key - user must provide their own

// Model configuration - using the actual available models from Google AI Studio
// Ordered from most available to least available (cheapest to most expensive)
// This ensures we preserve premium models with lower limits for when needed
const MODEL_CONFIG = [
  { name: 'gemini-2.5-flash-lite', displayName: 'Gemini 2.5 Flash Lite', daily: 1000, rpm: 15 },
  { name: 'gemini-2.5-flash', displayName: 'Gemini 2.5 Flash', daily: 250, rpm: 10 },
  { name: 'gemini-2.0-flash-lite', displayName: 'Gemini 2.0 Flash Lite', daily: 200, rpm: 30 },
  { name: 'gemini-2.0-flash', displayName: 'Gemini 2.0 Flash', daily: 200, rpm: 15 },
  { name: 'gemini-2.5-pro', displayName: 'Gemini 2.5 Pro', daily: 50, rpm: 2 }
];

// Track exhausted models for the day
let exhaustedModels = new Set();

// Function to get model usage from storage
async function getModelUsage() {
  try {
    const result = await chrome.storage.sync.get('modelUsage');
    return result.modelUsage || {};
  } catch (error) {
    console.error('Error getting model usage:', error);
    return {};
  }
}

// Function to save model usage to storage
async function saveModelUsage(usage) {
  try {
    await chrome.storage.sync.set({ modelUsage: usage });
  } catch (error) {
    console.error('Error saving model usage:', error);
  }
}

// Function to check if model is available
function isModelAvailable(modelName, usage) {
  const today = new Date().toDateString();
  const modelKey = `${modelName}_${today}`;
  const modelUsage = usage[modelKey] || 0;
  
  const model = MODEL_CONFIG.find(m => m.name === modelName);
  if (!model) return false;
  
  return modelUsage < model.daily;
}

// Function to increment model usage
async function incrementModelUsage(modelName) {
  const usage = await getModelUsage();
  const today = new Date().toDateString();
  const modelKey = `${modelName}_${today}`;
  
  usage[modelKey] = (usage[modelKey] || 0) + 1;
  await saveModelUsage(usage);
}

// Function to get API key from storage
async function getApiKey() {
  try {
    const result = await chrome.storage.sync.get('apiKey');
    return result.apiKey || DEFAULT_API_KEY;
  } catch (error) {
    console.error('Error getting API key:', error);
    return DEFAULT_API_KEY;
  }
}

// Main function to handle content analysis
async function handleContentAnalysis(data) {
  console.log('=== HANDLE CONTENT ANALYSIS CALLED ===');
  console.log('Starting content analysis...', { 
    content: data.content?.length, 
    images: data.images?.length, 
    screenshot: !!data.screenshot, 
    pageUrl: data.pageUrl 
  });
  
  try {
    // Get API key from storage
    const apiKey = await getApiKey();
    console.log('API key available:', !!apiKey);
    
    if (!apiKey) {
      return { error: 'API key not configured. Please set your Google Gemini API key in the extension settings. Get your free API key at https://makersuite.google.com/app/apikey' };
    }
    
    // Get current model usage
    const usage = await getModelUsage();
    
    // Find available model
    let selectedModel = null;
    for (const model of MODEL_CONFIG) {
      if (isModelAvailable(model.name, usage)) {
        selectedModel = model;
        break;
      }
    }
    
    if (!selectedModel) {
      return { error: 'All models exhausted for today. Try again tomorrow.' };
    }
    
    console.log('Selected model:', selectedModel.name);
    
    // Prepare the prompt
    const prompt = `Analyze the following content and provide a helpful response:

Page URL: ${data.pageUrl}
Content: ${data.content}

${data.images && data.images.length > 0 ? `Images: ${data.images.length} images provided` : ''}

Please provide a concise, helpful analysis of this content.`;

    // Prepare image parts if available
    const imageParts = [];
    if (data.images && data.images.length > 0) {
      for (const image of data.images) {
        imageParts.push({
          inline_data: {
            mime_type: image.mimeType,
            data: image.data
          }
        });
      }
    }
    
    // Call Gemini API
    console.log('=== CALLING GEMINI API ===');
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${selectedModel.name}:generateContent?key=${apiKey}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{
            parts: [
              { text: prompt },
              ...imageParts
            ]
          }],
          generationConfig: {
            temperature: 0.7,
            topK: 40,
            topP: 0.95,
            maxOutputTokens: 1024
          }
        })
      }
    );
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error:', response.status, errorText);
      try {
        const errorJson = JSON.parse(errorText);
        if (errorJson.error && errorJson.error.message) {
          return { error: errorJson.error.message };
        }
      } catch (e) {
        // If JSON parsing fails, use the raw text
      }
      return { error: `API Error: ${response.status} - ${errorText}` };
    }
    
    const result = await response.json();
    console.log('API Response:', result);
    
    if (!result.candidates || !result.candidates[0] || !result.candidates[0].content) {
      return { error: 'Invalid response from API' };
    }
    
    // Safe access to the response text
    let aiResponse = '';
    try {
      if (result.candidates[0].content.parts && result.candidates[0].content.parts[0] && result.candidates[0].content.parts[0].text) {
        aiResponse = result.candidates[0].content.parts[0].text;
      } else {
        aiResponse = 'No response text available';
      }
    } catch (error) {
      console.error('Error parsing API response:', error);
      return { error: 'Failed to parse API response: ' + error.message };
    }
    
    // Increment model usage
    await incrementModelUsage(selectedModel.name);
    
    return {
      success: true,
      response: aiResponse,
      model: selectedModel.name,
      usage: await getModelUsage()
    };
    
  } catch (error) {
    console.error('Error in handleContentAnalysis:', error);
    return { error: error.message };
  }
}

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'ANALYZE_CONTENT') {
    handleContentAnalysis(message.data).then(sendResponse);
    return true; // Keep channel open for async response
  }
});

console.log('Moodle Gemini Search background script loaded');
