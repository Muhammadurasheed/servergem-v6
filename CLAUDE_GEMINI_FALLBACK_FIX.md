# Claude Prompt: Fix Gemini API Fallback Issue

## Problem Summary
When Vertex AI quota is exhausted (429 error), the system attempts to fallback to Gemini API but fails with:
```
404 models/gemini-1.5-flash is not found for API version v1beta, or is not supported for generateContent
```

## Root Cause
The Gemini API SDK v0.8.5 uses the v1beta endpoint which expects model names WITHOUT the "models/" prefix. The current code uses `'models/gemini-1.5-flash'` which is incorrect for v1beta.

## Solution
Change model name from `'models/gemini-1.5-flash'` to `'gemini-1.5-flash'` (remove prefix).

## Files to Review and Modify

### 1. `backend/agents/orchestrator.py` (PRIMARY FIX)
**Lines to modify:** ~300-310

**Current (BROKEN):**
```python
backup_model = genai.GenerativeModel(
    'models/gemini-1.5-flash',  # ❌ WRONG for v1beta
    tools=[self._get_function_declarations_genai()],
    system_instruction=...
)
```

**Fixed:**
```python
backup_model = genai.GenerativeModel(
    'gemini-1.5-flash',  # ✅ CORRECT for v1beta (no prefix)
    tools=[self._get_function_declarations_genai()],
    system_instruction=...
)
```

### 2. `backend/agents/code_analyzer.py` (SECONDARY CHECK)
**Lines to check:** ~60-75

Ensure fallback code also uses correct model name:
```python
backup_model = genai.GenerativeModel('gemini-1.5-flash')  # No prefix
```

## Testing the Fix

1. **Trigger quota exhaustion**: Deploy a project to hit Vertex AI quota limit
2. **Verify fallback activation**: Look for log message:
   ```
   [Orchestrator] ✅ Activating fallback to Gemini API
   ```
3. **Confirm success**: Should see:
   ```
   [Orchestrator] ✅ Successfully switched to Gemini API
   ```

## Expected Logs (Success)
```
[Orchestrator] ⚠️ Quota error detected: 429 resource exhausted...
[Orchestrator] Fallback conditions:
  - Using Vertex AI: True
  - Gemini API key available: True
[Orchestrator] ✅ Activating fallback to Gemini API
[Orchestrator] ✅ Successfully switched to Gemini API
[Orchestrator] ✅ Now using Gemini API - deployment continues...
```

## Important Notes

### Model Naming Convention
- **Vertex AI** (v1): Uses `'gemini-1.5-flash'` (no prefix)
- **Gemini API v1beta**: Uses `'gemini-1.5-flash'` (no prefix)
- **Gemini API v1**: Would use `'models/gemini-1.5-flash'` (with prefix) - NOT used

### SDK Version
Current: `google-generativeai==0.8.5`
- This version uses v1beta endpoint
- Model names must NOT have "models/" prefix

### Fallback Flow
1. Vertex AI fails with 429 quota error
2. System detects ResourceExhausted exception
3. Check if Gemini API key exists
4. Create new GenerativeModel with Gemini API
5. Switch permanently to Gemini API
6. Continue deployment without user interruption

## Related Issues Fixed in This Session

### Real-Time Progress Updates
Added `await asyncio.sleep(0)` after WebSocket sends to force event loop flush:
- `backend/agents/orchestrator.py`: All progress message sends
- `backend/services/gcloud_service.py`: Build progress polling
- `backend/agents/code_analyzer.py`: Analysis progress
- `backend/services/analysis_service.py`: Analysis stages

### Deployment Progress Not Showing
Added real-time callbacks to:
- `build_progress()`: Forwards build updates to frontend
- `deploy_progress()`: Forwards deployment updates to frontend
Both include `await asyncio.sleep(0)` to flush immediately

## Quick Checklist
- [ ] Remove "models/" prefix from Gemini API model name
- [ ] Test quota exhaustion triggers fallback
- [ ] Verify fallback succeeds without 404 error
- [ ] Confirm deployment continues seamlessly
- [ ] Check real-time progress updates work
- [ ] Verify logs show successful API switch

---
**Key Insight**: The v1beta API endpoint expects plain model names. The "models/" prefix is only for certain v1 endpoints and will cause 404 errors in v1beta.
