"""
ServerGem Backend API
FastAPI server optimized for Google Cloud Run
بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime
import json
import uuid
import traceback

from agents.orchestrator import OrchestratorAgent
from services.deployment_service import deployment_service
from services.user_service import user_service
from services.usage_service import usage_service
from middleware.usage_tracker import UsageTrackingMiddleware
from models import DeploymentStatus, PlanTier

# Import progress notifier
import sys
sys.path.append(os.path.dirname(__file__))
from utils.progress_notifier import ProgressNotifier, DeploymentStages

load_dotenv()

app = FastAPI(
    title="ServerGem API",
    description="AI-powered Cloud Run deployment assistant",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Usage tracking middleware
app.add_middleware(UsageTrackingMiddleware)

# Store active WebSocket connections with metadata
active_connections: dict[str, dict] = {}

# Store orchestrator instances per session (CRITICAL FIX for deployment loop)
# This preserves project context across reconnections
session_orchestrators: dict[str, OrchestratorAgent] = {}

# Initialize global orchestrator (fallback only)
orchestrator = OrchestratorAgent(
    gcloud_project=os.getenv('GOOGLE_CLOUD_PROJECT'),
    github_token=os.getenv('GITHUB_TOKEN'),
    location=os.getenv('GOOGLE_CLOUD_REGION', 'us-central1')
)


class ChatMessage(BaseModel):
    message: str
    session_id: str


# ============================================================================
# HELPER FUNCTIONS FOR SAFE WEBSOCKET SENDING
# ============================================================================

async def safe_send_json(session_id: str, data: dict) -> bool:
    """
    Safely send JSON to WebSocket, handling all error cases.
    Returns True if sent successfully, False otherwise.
    """
    if session_id not in active_connections:
        print(f"[WebSocket] ⚠️  Session {session_id} not in active connections")
        return False
    
    connection_info = active_connections[session_id]
    websocket = connection_info['websocket']
    
    try:
        # Check if WebSocket is in a state that can send
        if websocket.client_state.name != "CONNECTED":
            print(f"[WebSocket] ⚠️  Session {session_id} not connected (state: {websocket.client_state.name})")
            return False
        
        # Try to send
        await websocket.send_json(data)
        print(f"[WebSocket] ✅ Sent to {session_id}: {data.get('type', 'unknown')}")
        return True
        
    except RuntimeError as e:
        if "close message has been sent" in str(e):
            print(f"[WebSocket] ⚠️  Session {session_id} already closed, removing from active connections")
            # Remove from active connections
            if session_id in active_connections:
                del active_connections[session_id]
            return False
        else:
            print(f"[WebSocket] ❌ RuntimeError sending to {session_id}: {e}")
            return False
            
    except Exception as e:
        print(f"[WebSocket] ❌ Error sending to {session_id}: {e}")
        return False


async def broadcast_to_session(session_id: str, data: dict):
    """Broadcast message to a specific session with retries"""
    max_retries = 3
    for attempt in range(max_retries):
        success = await safe_send_json(session_id, data)
        if success:
            return True
        
        if attempt < max_retries - 1:
            print(f"[WebSocket] 🔄 Retry {attempt + 1}/{max_retries} for session {session_id}")
            await asyncio.sleep(0.5)
    
    print(f"[WebSocket] ❌ Failed to send to {session_id} after {max_retries} attempts")
    return False


# ============================================================================
# SESSION CLEANUP TASK
# ============================================================================

async def cleanup_stale_sessions():
    """Periodically clean up inactive session orchestrators to free memory"""
    while True:
        try:
            await asyncio.sleep(3600)  # Check every hour
            
            current_time = datetime.now()
            stale_sessions = []
            
            for session_id in list(session_orchestrators.keys()):
                # Remove sessions that are not actively connected
                if session_id not in active_connections:
                    # Could add timestamp tracking here for more sophisticated cleanup
                    # For now, keep orchestrators for reconnections
                    pass
            
            if stale_sessions:
                for session_id in stale_sessions:
                    del session_orchestrators[session_id]
                print(f"[Cleanup] Removed {len(stale_sessions)} stale session orchestrators")
                
        except Exception as e:
            print(f"[Cleanup] Error in cleanup task: {e}")


@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup"""
    asyncio.create_task(cleanup_stale_sessions())
    print("[ServerGem] 🚀 Background cleanup task started")


# ============================================================================
# KEEP-ALIVE TASK
# ============================================================================

async def keep_alive_task(session_id: str):
    """Send periodic pings to keep connection alive"""
    while session_id in active_connections:
        try:
            await asyncio.sleep(30)  # Ping every 30 seconds
            
            if session_id in active_connections:
                await safe_send_json(session_id, {
                    'type': 'ping',
                    'timestamp': datetime.now().isoformat()
                })
                print(f"[WebSocket] 🏓 Heartbeat sent to {session_id}")
        except asyncio.CancelledError:
            print(f"[WebSocket] Keep-alive task cancelled for {session_id}")
            break
        except Exception as e:
            print(f"[WebSocket] ❌ Keep-alive error for {session_id}: {e}")
            break


# ============================================================================
# MAIN ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ServerGem",
        "status": "operational",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check for Cloud Run"""
    return {
        "status": "healthy",
        "service": "ServerGem Backend",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/chat")
async def chat(message: ChatMessage):
    """HTTP endpoint for chat (non-streaming)"""
    try:
        response = await orchestrator.process_message(
            message.message,
            message.session_id
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, api_key: Optional[str] = Query(None)):
    """
    WebSocket endpoint with bulletproof error handling
    بِسْمِ اللَّهِ - In the name of Allah, the Most Gracious, the Most Merciful
    """
    
    session_id = None
    user_api_key = api_key
    keep_alive = None
    
    try:
        # Vertex AI uses Google Cloud authentication - no API key needed
        gcloud_project = os.getenv('GOOGLE_CLOUD_PROJECT')
        gcloud_region = os.getenv('GOOGLE_CLOUD_REGION', 'us-central1')
        
        if not gcloud_project:
            await websocket.close(code=1008, reason="Google Cloud project not configured")
            return
        
        await websocket.accept()
        print(f"[WebSocket] ✅ Connection accepted (Using Vertex AI with project: {gcloud_project})")
        
        # Receive init message
        init_message = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=10.0
        )
        
        message_type = init_message.get('type')
        
        if message_type != 'init':
            await websocket.close(code=1008, reason="Expected init message")
            return
        
        session_id = init_message.get('session_id', f'session_{uuid.uuid4().hex[:12]}')
        instance_id = init_message.get('instance_id', 'unknown')
        is_reconnect = init_message.get('is_reconnect', False)
        
        print(f"[WebSocket] 🔌 Client connecting:")
        print(f"  Session ID: {session_id}")
        print(f"  Instance ID: {instance_id}")
        print(f"  Reconnect: {is_reconnect}")
        
        # Handle reconnection
        if session_id in active_connections:
            print(f"[WebSocket] 🔄 Reconnection detected for {session_id}")
            old_connection = active_connections[session_id]
            old_ws = old_connection['websocket']
            old_keep_alive = old_connection.get('keep_alive_task')
            
            # Cancel old keep-alive task
            if old_keep_alive and not old_keep_alive.done():
                old_keep_alive.cancel()
                try:
                    await old_keep_alive
                except asyncio.CancelledError:
                    pass
            
            # Close old WebSocket gracefully
            try:
                await old_ws.close(code=1000, reason="Client reconnected")
            except:
                pass
        
        # Store new connection
        keep_alive = asyncio.create_task(keep_alive_task(session_id))
        
        active_connections[session_id] = {
            'websocket': websocket,
            'keep_alive_task': keep_alive,
            'connected_at': datetime.now().isoformat(),
            'instance_id': instance_id
        }
        
        print(f"[WebSocket] ✅ Session {session_id} registered. Active: {len(active_connections)}")
        
        # CRITICAL FIX: Reuse existing orchestrator for this session or create new one
        # This preserves project context (including cloned repo info) across reconnections
        if session_id in session_orchestrators:
            user_orchestrator = session_orchestrators[session_id]
            print(f"[WebSocket] ♻️  Reusing existing orchestrator for {session_id}")
            print(f"[WebSocket] 📦 Context preserved: {list(user_orchestrator.project_context.keys())}")
        else:
            # Extract Gemini API key from query params (from user's localStorage)
            gemini_key = user_api_key  # This was extracted from query params earlier
            
            user_orchestrator = OrchestratorAgent(
                gcloud_project=gcloud_project,
                github_token=os.getenv('GITHUB_TOKEN'),
                location=gcloud_region,
                gemini_api_key=gemini_key  # Pass user's API key for fallback
            )
            session_orchestrators[session_id] = user_orchestrator
            
            mode = "Vertex AI" if not gemini_key else "Gemini API (user key)"
            print(f"[WebSocket] ✨ Created new orchestrator for {session_id} - Mode: {mode}")
        
        # Get or initialize session env vars from orchestrator context
        session_env_vars = user_orchestrator.project_context.get('env_vars', {})
        
        # Send connection confirmation
        await safe_send_json(session_id, {
            'type': 'connected',
            'session_id': session_id,
            'message': 'Connected to ServerGem AI - Ready to deploy!'
        })
        
        # Message loop with timeout
        while True:
            try:
                # Use timeout to allow periodic checks
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=60.0  # 1 minute timeout
                )
            except asyncio.TimeoutError:
                # Timeout is OK, just continue loop
                continue
            except RuntimeError as e:
                # WebSocket disconnected while waiting for message
                print(f"[WebSocket] ⚠️ RuntimeError in receive loop for {session_id}: {e}")
                break
            except WebSocketDisconnect:
                # Client disconnected normally
                print(f"[WebSocket] 🔌 Client {session_id} disconnected during receive")
                break
            except Exception as e:
                # Any other error during receive
                print(f"[WebSocket] ❌ Error receiving from {session_id}: {e}")
                break
            
            msg_type = data.get('type')
            
            # Handle pong response
            if msg_type == 'pong':
                print(f"[WebSocket] 🏓 Pong received from {session_id}")
                continue
            
            # Handle env vars
            if msg_type == 'env_vars_uploaded':
                variables = data.get('variables', [])
                count = data.get('count', len(variables))
                
                print(f"[WebSocket] 📦 Received {count} env vars")
                
                # Store env vars in both session and orchestrator context
                for var in variables:
                    session_env_vars[var['key']] = {
                        'value': var['value'],
                        'isSecret': var.get('isSecret', False)
                    }
                
                user_orchestrator.project_context['env_vars'] = session_env_vars
                print(f"[WebSocket] ✅ Env vars stored: {count} variables")
                
                # Format list
                env_list = '\n'.join([
                    f'• {key} {"(Secret 🔒)" if val["isSecret"] else ""}'
                    for key, val in session_env_vars.items()
                ])
                
                confirmation_msg = f"""✅ Configuration received successfully!

**Uploaded:**
{env_list}

All secrets will be stored securely in Google Secret Manager.

**Next Step:** Say 'deploy' or 'yes' to start deployment!"""
                
                await safe_send_json(session_id, {
                    'type': 'message',
                    'data': {
                        'content': confirmation_msg,
                        'intent': 'env_vars_confirmed',
                        'metadata': {
                            'env_vars_count': count,
                            'secrets_count': sum(1 for v in session_env_vars.values() if v['isSecret'])
                        }
                    },
                    'timestamp': datetime.now().isoformat()
                })
                
                continue
            
            # Handle chat messages
            if msg_type == 'message':
                message = data.get('message')
                metadata = data.get('metadata', {})  # ✅ Extract metadata
                
                if not message:
                    continue
                
                # ✅ CRITICAL FIX: Update GitHub token from metadata if provided
                # This is sent from Deploy.tsx when selecting a repo
                github_token = metadata.get('githubToken')
                if github_token:
                    print(f"[WebSocket] 🔑 Updating GitHub token for session {session_id}")
                    # Update the orchestrator's GitHub service with the new token
                    from services.github_service import GitHubService
                    user_orchestrator.github_service = GitHubService(github_token)
                    print(f"[WebSocket] ✅ GitHub token updated successfully")
                
                # Typing indicator
                await safe_send_json(session_id, {
                    'type': 'typing',
                    'timestamp': datetime.now().isoformat()
                })
                
                # Check for deployment keywords
                deployment_keywords = ['deploy', 'start', 'begin', 'launch', 'go ahead', 'yes', 'proceed']
                might_deploy = any(keyword in message.lower() for keyword in deployment_keywords)
                
                # Create progress notifier
                progress_notifier = None
                if might_deploy:
                    deployment_id = f"deploy-{uuid.uuid4().hex[:8]}"
                    # Pass session_id and safe_send function
                    progress_notifier = ProgressNotifier(
                        session_id, 
                        deployment_id, 
                        safe_send_json  # Pass the safe send function!
                    )
                    print(f"[WebSocket] ✨ Created progress notifier: {deployment_id}")
                    
                    # Send deployment started
                    await safe_send_json(session_id, {
                        "type": "deployment_started",
                        "deployment_id": deployment_id,
                        "message": "🚀 Starting deployment process...",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Process message
                try:
                    response = await user_orchestrator.process_message(
                        message,
                        session_id,
                        progress_notifier=progress_notifier,
                        safe_send=safe_send_json  # Pass safe_send for progress messages during analysis
                    )
                    
                    # Send response
                    await safe_send_json(session_id, {
                        'type': 'message',
                        'data': response,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"[WebSocket] ❌ Error processing message: {error_msg}")
                    print(traceback.format_exc())
                    
                    # Send error
                    if '429' in error_msg or 'quota' in error_msg.lower():
                        await safe_send_json(session_id, {
                            'type': 'error',
                            'message': 'API quota exceeded. Please try again later.',
                            'code': 'QUOTA_EXCEEDED',
                            'timestamp': datetime.now().isoformat()
                        })
                    elif '401' in error_msg or '403' in error_msg:
                        await safe_send_json(session_id, {
                            'type': 'error',
                            'message': 'Invalid API key. Please check Settings.',
                            'code': 'INVALID_API_KEY',
                            'timestamp': datetime.now().isoformat()
                        })
                    else:
                        await safe_send_json(session_id, {
                            'type': 'error',
                            'message': f'Error: {error_msg}',
                            'code': 'API_ERROR',
                            'timestamp': datetime.now().isoformat()
                        })
    
    except WebSocketDisconnect:
        print(f"[WebSocket] 🔌 Client {session_id} disconnected normally")
    
    except asyncio.TimeoutError:
        print(f"[WebSocket] ⏰ Timeout for {session_id}")
    
    except Exception as e:
        print(f"[WebSocket] ❌ Error for {session_id}: {e}")
        print(traceback.format_exc())
    
    finally:
        # Cleanup
        if session_id and session_id in active_connections:
            connection_info = active_connections[session_id]
            
            # Cancel keep-alive
            if keep_alive and not keep_alive.done():
                keep_alive.cancel()
                try:
                    await keep_alive
                except asyncio.CancelledError:
                    pass
            
            # Remove from active connections
            del active_connections[session_id]
            print(f"[WebSocket] 🧹 Cleaned up connection for {session_id}. Active: {len(active_connections)}")
            
            # NOTE: We DON'T delete from session_orchestrators here
            # This preserves context for reconnections within the same session
            # Orchestrators will be cleaned up by a periodic cleanup task or session timeout


# ============================================================================
# User Management Endpoints
# ============================================================================

@app.post("/api/users")
async def create_user(
    email: str,
    username: str,
    display_name: str,
    avatar_url: Optional[str] = None,
    github_token: Optional[str] = None
):
    """Create new user account"""
    existing = user_service.get_user_by_email(email)
    if existing:
        return {"user": existing.to_dict(), "existing": True}
    
    user = user_service.create_user(
        email=email,
        username=username,
        display_name=display_name,
        avatar_url=avatar_url,
        github_token=github_token
    )
    
    return {"user": user.to_dict(), "existing": False}


@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    """Get user by ID"""
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


@app.patch("/api/users/{user_id}")
async def update_user(user_id: str, updates: dict):
    """Update user"""
    user = user_service.update_user(user_id, **updates)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


@app.post("/api/users/{user_id}/upgrade")
async def upgrade_user(user_id: str, tier: str):
    """Upgrade user plan"""
    try:
        plan_tier = PlanTier(tier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    user = user_service.upgrade_user_plan(user_id, plan_tier)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"user": user.to_dict(), "message": f"Upgraded to {tier}"}


# ============================================================================
# Deployment Management Endpoints
# ============================================================================

@app.get("/api/deployments")
async def list_deployments(user_id: str = Query(...)):
    """Get all deployments for user"""
    deployments = deployment_service.get_user_deployments(user_id)
    return {
        "deployments": [d.to_dict() for d in deployments],
        "count": len(deployments)
    }


@app.get("/api/deployments/{deployment_id}")
async def get_deployment(deployment_id: str):
    """Get deployment by ID"""
    deployment = deployment_service.get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment.to_dict()


@app.post("/api/deployments")
async def create_deployment(
    user_id: str,
    service_name: str,
    repo_url: str,
    region: str = "us-central1",
    env_vars: dict = None
):
    """Create new deployment"""
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    active_count = len(deployment_service.get_active_deployments(user_id))
    if not user.can_deploy_more_services(active_count):
        raise HTTPException(
            status_code=403,
            detail=f"Deployment limit reached. Upgrade to deploy more services."
        )
    
    deployment = deployment_service.create_deployment(
        user_id=user_id,
        service_name=service_name,
        repo_url=repo_url,
        region=region,
        env_vars=env_vars
    )
    
    usage_service.track_deployment(user_id)
    
    return deployment.to_dict()


@app.patch("/api/deployments/{deployment_id}/status")
async def update_deployment_status(
    deployment_id: str,
    status: str,
    error_message: Optional[str] = None,
    gcp_url: Optional[str] = None
):
    """Update deployment status"""
    try:
        status_enum = DeploymentStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    deployment = deployment_service.update_deployment_status(
        deployment_id,
        status_enum,
        error_message=error_message,
        gcp_url=gcp_url
    )
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return deployment.to_dict()


@app.delete("/api/deployments/{deployment_id}")
async def delete_deployment(deployment_id: str):
    """Delete deployment"""
    success = deployment_service.delete_deployment(deployment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return {"message": "Deployment deleted successfully"}


@app.get("/api/deployments/{deployment_id}/events")
async def get_deployment_events(deployment_id: str, limit: int = 50):
    """Get deployment event log"""
    events = deployment_service.get_deployment_events(deployment_id, limit)
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


@app.post("/api/deployments/{deployment_id}/logs")
async def add_deployment_log(deployment_id: str, log_line: str):
    """Add build log line"""
    deployment_service.add_build_log(deployment_id, log_line)
    return {"message": "Log added"}


# ============================================================================
# Usage & Analytics Endpoints
# ============================================================================

@app.get("/api/usage/{user_id}/today")
async def get_today_usage(user_id: str):
    """Get today's usage for user"""
    usage = usage_service.get_today_usage(user_id)
    user = user_service.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "usage": usage.to_dict(),
        "limits": {
            "max_services": user.max_services,
            "max_requests_per_day": user.max_requests_per_day,
            "max_memory_mb": user.max_memory_mb
        },
        "plan_tier": user.plan_tier.value
    }


@app.get("/api/usage/{user_id}/summary")
async def get_usage_summary(user_id: str, days: int = 30):
    """Get usage summary for last N days"""
    summary = usage_service.get_usage_summary(user_id, days)
    return summary


@app.get("/api/usage/{user_id}/monthly")
async def get_monthly_usage(user_id: str, year: int, month: int):
    """Get monthly usage"""
    usage_list = usage_service.get_monthly_usage(user_id, year, month)
    return {
        "usage": [u.to_dict() for u in usage_list],
        "month": f"{year}-{month:02d}"
    }


# ============================================================================
# Stats & Health
# ============================================================================

@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    return {
        "active_connections": len(active_connections),
        "total_deployments": len(deployment_service._deployments),
        "total_users": len(user_service._users)
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )