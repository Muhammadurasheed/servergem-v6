# Master Prompt: Fix Real-Time Deployment Progress Updates

## Context
You are acting as a team of CTOs and Principal Engineers from FAANG companies. You have been tasked with fixing a critical UX issue in a Google Cloud Run deployment platform built with Python FastAPI backend and React TypeScript frontend, connected via WebSockets.

## The Critical Problem
After a user submits a repository URL for deployment, there is a **severe delay** (several seconds to minutes) before any visual feedback appears in the frontend. The current behavior:

1. User submits repo URL
2. Frontend shows three bouncing dots that disappear after 3 seconds
3. UI becomes completely static with NO updates
4. Backend is actively working (cloning repo, analyzing code, generating Dockerfile, building container)
5. **Only after ALL backend work completes**, the WebSocket suddenly dumps all logs at once
6. Result: Users think the platform is broken and abandon it

## Expected Behavior (FAANG-Level UX)
1. User submits repo URL
2. **IMMEDIATELY** see "Cloning repository..." with progress
3. **Real-time updates** as each agent works: "Analyzing Python dependencies...", "Detected Flask application...", "Generating optimized Dockerfile..."
4. **Live streaming** of deployment stages with granular progress
5. User stays engaged and confident throughout the entire process

## Your Mission
Investigate and fix why real-time WebSocket messages are NOT being sent during the deployment process. The issue is likely:
- Backend not emitting WebSocket events during execution
- Progress notifier not being called at the right moments
- WebSocket messages being buffered instead of streamed
- Frontend not listening to the correct message types

## Investigation Checklist

### Phase 1: Backend Investigation
1. **Trace the deployment flow in `orchestrator.py`:**
   - Does it call `progress_notifier.start_stage()` BEFORE starting each stage?
   - Are there `await` statements that block progress updates?
   - Is `safe_send` actually sending messages to the WebSocket?

2. **Check `progress_notifier.py`:**
   - Is `send_update()` being called frequently enough?
   - Are messages being queued or sent immediately?
   - Is the `safe_send_func` parameter actually the WebSocket send function?

3. **Examine `app.py` WebSocket handling:**
   - Is `safe_send` defined correctly?
   - Are messages being sent in real-time or batched?
   - Is there any buffering happening?

4. **Review service files:**
   - Do `github_service.py`, `analysis_service.py`, `docker_service.py`, `gcloud_service.py` call progress updates during their work?
   - Are they yielding control back to the event loop?

### Phase 2: Frontend Investigation
1. **Check `useChat.ts`:**
   - Is it listening for `deployment_started`, `deployment_progress` messages?
   - Is the `activeDeployment` state being updated correctly?
   - Are WebSocket message handlers set up before the deployment starts?

2. **Examine `WebSocketContext.tsx` and `WebSocketClient.ts`:**
   - Are messages being processed immediately or queued?
   - Is there any debouncing or throttling?

3. **Verify `ChatMessage.tsx` and `DeploymentLogs.tsx`:**
   - Do they re-render on state updates?
   - Is the UI updating when `activeDeployment` changes?

## Required Fixes (Expected Solutions)

### Backend Fixes
1. **Ensure progress_notifier is called at EVERY step:**
   ```python
   # In orchestrator.py, BEFORE each operation:
   progress_notifier.start_stage(STAGE_REPO_CLONE, "Cloning repository...")
   result = await github_service.clone_repo(repo_url)
   progress_notifier.complete_stage(STAGE_REPO_CLONE, "Repository cloned successfully")
   ```

2. **Add granular progress updates INSIDE long-running operations:**
   ```python
   # In analysis_service.py:
   progress_notifier.update_progress(STAGE_CODE_ANALYSIS, "Scanning Python files...", 25)
   # ... analyze files ...
   progress_notifier.update_progress(STAGE_CODE_ANALYSIS, "Detecting framework...", 50)
   ```

3. **Ensure WebSocket sends are not blocked:**
   - Use `asyncio.create_task()` for non-blocking sends
   - Verify `safe_send` doesn't have `await` that blocks the flow

### Frontend Fixes
1. **Ensure WebSocket listeners are registered BEFORE sending the deployment request**
2. **Update `activeDeployment` state immediately upon receiving ANY deployment message**
3. **Ensure `DeploymentLogs` component renders progressively, not just at the end**

## Success Criteria
- [ ] User sees "Cloning repository..." within 100ms of clicking deploy
- [ ] Progress updates appear every 1-2 seconds during deployment
- [ ] Each AI agent's actions are visible in real-time
- [ ] No more than 3 seconds pass without a UI update during active deployment
- [ ] Users never see a static screen during deployment

## Implementation Standards
- **FAANG-level code quality**: Clean, maintainable, well-commented
- **Error handling**: Graceful degradation if WebSocket fails
- **Performance**: No blocking operations in the main flow
- **UX**: Delightful, confidence-inspiring progress updates

## Files You Need to Analyze
**Backend (Python):**
1. `backend/app.py` - Main Flask app with WebSocket handling
2. `backend/agents/orchestrator.py` - Deployment orchestration logic
3. `backend/utils/progress_notifier.py` - Progress notification utility
4. `backend/services/deployment_service.py` - Deployment service
5. `backend/services/github_service.py` - Repository cloning
6. `backend/services/analysis_service.py` - Code analysis
7. `backend/services/docker_service.py` - Dockerfile generation
8. `backend/services/gcloud_service.py` - Cloud Run deployment
9. `backend/services/health_check.py` - Health verification

**Frontend (TypeScript/React):**
1. `src/hooks/useChat.ts` - Chat state and WebSocket message handling
2. `src/components/ChatMessage.tsx` - Message rendering
3. `src/components/chat/DeploymentLogs.tsx` - Real-time deployment logs UI
4. `src/contexts/WebSocketContext.tsx` - WebSocket provider
5. `src/lib/websocket/WebSocketClient.ts` - WebSocket client implementation
6. `src/types/websocket.ts` - WebSocket message types
7. `src/types/deployment.ts` - Deployment types and stages

**Configuration:**
1. `PHASE2_CLOUDRUN_HARDENING.md` - Phase 2 implementation details
2. `backend/utils/progress_notifier.py` - Progress notification constants

## Your Approach
1. **Read ALL files listed above carefully**
2. **Trace the complete flow** from user click → backend processing → WebSocket emission → frontend update
3. **Identify the exact bottleneck** where real-time updates are lost
4. **Implement surgical fixes** with minimal changes, maximum impact
5. **Test the flow mentally** to ensure updates stream in real-time

## Invocation
Bismillah ar-Rahman ar-Rahim. 
La hawla wa la quwwata illa billah.
Allahumma salli ala Muhammad wa ala ali Muhammad.

Begin your investigation now. Read the files systematically, identify the root cause, and provide a detailed fix that achieves FAANG-level real-time deployment progress updates.

Allahu Musta'an.
