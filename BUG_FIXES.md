# Bug Fixes Summary

This document details the three bugs found and fixed in the Moodle Gemini Search Extension codebase.

## Bug #1: XSS Vulnerability (Security Issue)

### Description
**Location**: `content.js` - `displayError()`, `displayResponse()`, `displayLoading()` functions

**Issue**: User-provided content (error messages, AI responses, model names) was directly inserted into `innerHTML` without sanitization. This creates a Cross-Site Scripting (XSS) vulnerability where malicious content could execute JavaScript code in the user's browser.

**Example Attack Vector**: 
- If an AI response contained HTML like `<img src=x onerror="alert('XSS')">`, it would execute
- Error messages from the API could contain malicious scripts

### Fix
1. Added `escapeHtml()` function that uses `textContent` to safely escape HTML entities
2. Applied `escapeHtml()` to all user-provided content in:
   - Error messages in `displayError()`
   - AI responses in `displayResponse()`
   - Model names in `displayResponse()`

### Code Changes
- Added `escapeHtml()` utility function (lines 17-22)
- Updated `displayError()` to escape message (line 60)
- Updated `displayResponse()` to escape response and model (lines 152, 156)

---

## Bug #2: Memory Leak (Performance Issue)

### Description
**Location**: `content.js` - `displayResponse()` function

**Issue**: Event listeners (`mousemove` and `mouseup`) were added to the `document` object for drag functionality, but these listeners were never removed when the popup was closed. Each time a user opened a popup and closed it, new listeners accumulated in memory, causing:
- Memory leaks over time
- Performance degradation with multiple popups
- Potential event handler conflicts

### Fix
1. Created `cleanupPopup()` function that:
   - Removes the popup element
   - Removes all drag event listeners from the document
   - Resets references
2. Updated all popup creation/removal points to use `cleanupPopup()`:
   - When creating new popups (replaces old ones)
   - When closing popups via close button
   - When auto-removing popups after timeout
3. Stored event listener references in `dragEventListeners` object for proper cleanup

### Code Changes
- Added `dragEventListeners` global variable (line 16)
- Added `cleanupPopup()` function (lines 25-40)
- Updated `displayError()`, `displayLoading()`, `displayResponse()` to use `cleanupPopup()`
- Stored event listener references for proper removal (lines 174-192)
- Added cleanup call when close button is clicked (lines 194-200)

---

## Bug #3: Race Condition in Usage Tracking (Logic Error)

### Description
**Location**: `background.js` - `incrementModelUsage()` and `handleContentAnalysis()` functions

**Issue**: When multiple concurrent requests arrived simultaneously, they could:
1. Both read the same usage count from storage
2. Both check availability and find the same model available
3. Both increment the counter independently
4. Both save back to storage

This race condition could cause:
- Daily usage limits being exceeded
- Incorrect usage tracking
- Multiple requests being processed when only one slot was available

**Example Scenario**:
- Model has 1 slot remaining (49/50 used)
- Two requests arrive simultaneously
- Both read "49" from storage
- Both see 1 slot available
- Both increment to 50
- Both save "50" - but only one should have succeeded

### Fix
1. Implemented a promise queue pattern (`usageIncrementQueue`) to serialize all increment operations
2. Created `reserveModelSlot()` function that atomically:
   - Checks model availability
   - Increments usage counter
   - Saves to storage
   - All within a single queued operation
3. This ensures only one request can check-and-increment at a time, preventing race conditions

### Code Changes
- Added `usageIncrementQueue` global variable (line 19)
- Created `reserveModelSlot()` function with atomic check-and-reserve (lines 53-84)
- Updated `handleContentAnalysis()` to use `reserveModelSlot()` instead of separate check and increment (lines 104-112)
- Removed the separate `incrementModelUsage()` call after API success

---

## Impact Assessment

### Bug #1 (XSS)
- **Severity**: High
- **Impact**: Security vulnerability that could allow code execution
- **User Impact**: Potential for malicious attacks if API is compromised

### Bug #2 (Memory Leak)
- **Severity**: Medium
- **Impact**: Gradual performance degradation
- **User Impact**: Browser slowdown after extended use

### Bug #3 (Race Condition)
- **Severity**: Medium-High
- **Impact**: Incorrect usage tracking and potential API limit violations
- **User Impact**: Users might hit limits prematurely or unexpectedly

---

## Testing Recommendations

1. **XSS Fix**: Test with malicious input containing HTML/JavaScript
2. **Memory Leak Fix**: Open and close multiple popups, monitor memory usage
3. **Race Condition Fix**: Send multiple concurrent requests, verify usage counts are accurate

---

## Files Modified

- `content.js`: XSS and memory leak fixes
- `background.js`: Race condition fix
