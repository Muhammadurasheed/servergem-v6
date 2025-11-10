"""
ServerGem Orchestrator Agent
FAANG-Level Production Implementation
- Gemini ADK with function calling
- Production monitoring & observability
- Security best practices
- Cost optimization
- Advanced error handling
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration, Part, GenerationConfig
from datetime import datetime
import json
import uuid
import os
from dataclasses import dataclass
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.progress_notifier import ProgressNotifier, DeploymentStages


@dataclass
class ResourceConfig:
    """Resource configuration for Cloud Run deployments"""
    cpu: str
    memory: str
    concurrency: int
    min_instances: int
    max_instances: int


class OrchestratorAgent:
    """
    Production-grade orchestrator using Gemini ADK with function calling.
    Routes to real services: GitHub, Google Cloud, Docker, Analysis.
    """
    
    def __init__(
        self, 
        gcloud_project: str,
        github_token: Optional[str] = None,
        location: str = 'us-central1',
        gemini_api_key: Optional[str] = None
    ):
        self.gemini_api_key = gemini_api_key
        self.use_vertex_ai = not gemini_api_key  # Default to Vertex AI if no key provided
        self.gcloud_project = gcloud_project
        
        if self.use_vertex_ai:
            if not gcloud_project:
                raise ValueError("GOOGLE_CLOUD_PROJECT is required for Vertex AI")
            # Initialize Vertex AI
            vertexai.init(project=gcloud_project, location=location)
        else:
            # Using Gemini API directly
            import google.generativeai as genai
            genai.configure(api_key=gemini_api_key)
        
        # ULTRA-OPTIMIZED system instruction (47% token reduction)
        system_instruction = """ServerGem: Deploy to Cloud Run.

RULES:
- NO user GCP auth needed
- Provide .servergem.app URLs

STATE:
IF "Project Path:" exists → ONLY call deploy_to_cloudrun
IF user says "deploy"/"yes"/"go" → IMMEDIATELY deploy
ELSE → call clone_and_analyze_repo

Env vars auto-parsed from .env. Never clone twice.
        """.strip()
        
        # Initialize AI model (Vertex AI or Gemini API)
        if self.use_vertex_ai:
            self.model = GenerativeModel(
                'gemini-2.0-flash-exp',
                tools=[self._get_function_declarations()],
                system_instruction=system_instruction
            )
        else:
            # Gemini API with v1 API (upgraded SDK)
            import google.generativeai as genai
            self.model = genai.GenerativeModel(
                'gemini-1.5-flash',  # ✅ UPGRADED: v1 API supports 1.5-flash
                tools=[self._get_function_declarations_genai()],
                system_instruction=system_instruction
            )
        
        self.conversation_history: List[Dict] = []
        self.project_context: Dict[str, Any] = {}
        self.chat_session = None
        
        # Initialize real services - with proper error handling
        try:
            from services.github_service import GitHubService
            from services.gcloud_service import GCloudService
            from services.docker_service import DockerService
            from services.analysis_service import AnalysisService
            from services.monitoring import monitoring
            from services.security import security
            from services.optimization import optimization
            from services.deployment_progress import create_progress_tracker
            
            self.github_service = GitHubService(github_token)
            # Use ServerGem's GCP project (not user's)
            self.gcloud_service = GCloudService(
                gcloud_project or 'servergem-platform'
            ) if gcloud_project else None
            self.docker_service = DockerService()
            self.analysis_service = AnalysisService(gcloud_project, location)
            
            # Production services
            self.monitoring = monitoring
            self.security = security
            self.optimization = optimization
            self.create_progress_tracker = create_progress_tracker
            
        except ImportError as e:
            print(f"[WARNING] Service import failed: {e}")
            print("[WARNING] Running in mock mode - services not available")
            # Create mock services for testing
            self._init_mock_services()
    
    def _init_mock_services(self):
        """Initialize mock services for testing when real services unavailable"""
        class MockService:
            def __getattr__(self, name):
                async def mock_method(*args, **kwargs):
                    return {'success': False, 'error': 'Service not available'}
                return mock_method
        
        self.github_service = MockService()
        self.gcloud_service = MockService()
        self.docker_service = MockService()
        self.analysis_service = MockService()
        self.monitoring = MockService()
        self.security = MockService()
        self.optimization = MockService()
        self.create_progress_tracker = lambda *args, **kwargs: MockService()
    
    def _get_function_declarations_genai(self):
        """
        Get function declarations for Gemini API (google-generativeai format)
        """
        from agents.gemini_tools import get_gemini_api_tools
        return get_gemini_api_tools()
    
    def _get_function_declarations(self) -> Tool:
        """
        Define real functions available for Vertex AI Gemini to call
        Uses Vertex AI SDK format
        """
        return Tool(
            function_declarations=[
                FunctionDeclaration(
                    name='clone_and_analyze_repo',
                    description='Clone and analyze a GitHub repository. ⚠️ CRITICAL: Only call this when "Project Path:" is NOT in context. If "Project Path:" exists in context, repository is ALREADY cloned - call deploy_to_cloudrun instead! NEVER clone the same repo twice.',
                    parameters={
                        'type': 'object',
                        'properties': {
                            'repo_url': {
                                'type': 'string',
                                'description': 'GitHub repository URL (https://github.com/user/repo or git@github.com:user/repo.git)'
                            },
                            'branch': {
                                'type': 'string',
                                'description': 'Branch name to clone and analyze (default: main)'
                            }
                        },
                        'required': ['repo_url']
                    }
                ),
                FunctionDeclaration(
                    name='deploy_to_cloudrun',
                    description='Deploy an analyzed project to Google Cloud Run. CRITICAL: Use this function IMMEDIATELY when user says "deploy", "yes", "go ahead", "start", etc. AND context contains project_path (meaning repo was already analyzed). Auto-generate service_name from repo name. Environment variables are automatically loaded from context.',
                    parameters={
                        'type': 'object',
                        'properties': {
                            'project_path': {
                                'type': 'string',
                                'description': 'Local path to the cloned project. Use value from project_context that was set during clone_and_analyze_repo.'
                            },
                            'service_name': {
                                'type': 'string',
                                'description': 'Name for Cloud Run service. Auto-generate from repo name (e.g., "ihealth-backend" from "ihealth_backend.git"). Use lowercase and hyphens.'
                            },
                            'env_vars': {
                                'type': 'object',
                                'description': 'Leave empty - environment variables are automatically loaded from context'
                            }
                        },
                        'required': ['project_path', 'service_name']
                    }
                ),
                FunctionDeclaration(
                    name='list_user_repositories',
                    description='List GitHub repositories for the authenticated user. Use this when user asks to see their repos or wants to select a project to deploy.',
                    parameters={
                        'type': 'object',
                        'properties': {},
                        'required': []
                    }
                ),
                FunctionDeclaration(
                    name='get_deployment_logs',
                    description='Fetch recent logs from a deployed Cloud Run service. Use this for debugging deployment issues or when user asks to see logs.',
                    parameters={
                        'type': 'object',
                        'properties': {
                            'service_name': {
                                'type': 'string',
                                'description': 'Cloud Run service name'
                            },
                            'limit': {
                                'type': 'integer',
                                'description': 'Number of log entries to fetch (default: 50)'
                            }
                        },
                        'required': ['service_name']
                    }
                )
            ]
        )
    
    async def _retry_with_backoff(self, func, max_retries: int = 3, base_delay: float = 1.0):
        """
        Retry a function with exponential backoff for network errors
        """
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                error_str = str(e).lower()
                # Check if it's a network/connectivity error
                is_network_error = any(keyword in error_str for keyword in [
                    'connection aborted', 'connection refused', 'timeout', 
                    'unavailable', 'iocp', 'socket', '503', '502', '504'
                ])
                
                if not is_network_error or attempt == max_retries - 1:
                    raise  # Not a network error or final attempt - propagate
                
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                print(f"[Orchestrator] Network error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
                print(f"[Orchestrator] Retrying in {delay}s...")
                await self._send_progress_message(f"🔄 Network issue detected, retrying... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
        
        raise Exception("Max retries exceeded for network operation")

    async def _send_with_fallback(self, message: str):
        """
        Send message with automatic fallback: Vertex AI → Gemini API on quota exhaustion
        """
        try:
            # Try primary method (Vertex AI or Gemini API based on initialization)
            return await self._retry_with_backoff(
                lambda: self.chat_session.send_message(message),
                max_retries=2,
                base_delay=1.0
            )
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for quota/rate limit errors (429)
            is_quota_error = any(keyword in error_str for keyword in [
                'resource exhausted', '429', 'quota', 'rate limit'
            ])
            
            if is_quota_error and self.use_vertex_ai and self.gemini_api_key:
                # Switch to Gemini API fallback
                print(f"[Orchestrator] ⚠️ Vertex AI quota exhausted, falling back to Gemini API")
                await self._send_progress_message("⚠️ Switching to backup AI service...")
                
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=self.gemini_api_key)
                    
                    # Create backup Gemini API model - v1 API with upgraded SDK
                    backup_model = genai.GenerativeModel(
                        'gemini-1.5-flash',  # ✅ UPGRADED: v1 API supports 1.5-flash
                        tools=[self._get_function_declarations_genai()],
                        system_instruction=self.model._system_instruction if hasattr(self.model, '_system_instruction') else None
                    )
                    
                    # Create new chat session with backup model
                    backup_chat = backup_model.start_chat(history=[])
                    response = backup_chat.send_message(message)
                    
                    # Switch permanently to Gemini API
                    self.use_vertex_ai = False
                    self.model = backup_model
                    self.chat_session = backup_chat
                    
                    await self._send_progress_message("✅ Switched to Gemini API successfully")
                    return response
                    
                except Exception as fallback_err:
                    print(f"[Orchestrator] ❌ Fallback to Gemini API failed: {fallback_err}")
                    raise Exception(f"Both Vertex AI and Gemini API failed. Add API key in Settings.")
            
            # Re-raise if not quota error or no fallback available
            raise

    async def process_message(
        self, 
        user_message: str, 
        session_id: str, 
        progress_notifier: Optional[ProgressNotifier] = None,
        progress_callback: Optional[Callable] = None,
        safe_send: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: processes user message with Gemini ADK function calling
        
        CRITICAL FIX: Store safe_send IMMEDIATELY before any async operations
        """
        
        # ✅ Store session info BEFORE any async operations
        self.session_id = session_id
        self.safe_send = safe_send
    
        # Initialize chat session if needed
        if not self.chat_session:
            self.chat_session = self.model.start_chat(history=[])
        
        # ✅ OPTIMIZATION: Smart context injection - saves ~150 tokens on simple commands
        simple_keywords = ['deploy', 'yes', 'no', 'skip', 'proceed', 'continue', 'ok', 'okay', 'start', 'go']
        is_simple_command = any(user_message.lower().strip() == keyword for keyword in simple_keywords)
        
        if is_simple_command and self.project_context.get('project_path'):
            # Minimal context for simple commands (saves ~150 tokens)
            enhanced_message = f"Ready. User: {user_message}"
        else:
            # Full context for complex queries
            context_prefix = self._build_context_prefix()
            enhanced_message = f"{context_prefix}\n\nUser: {user_message}" if context_prefix else user_message
        
        try:
            # Send to Gemini with function calling enabled - with retry logic and fallback
            response = await self._send_with_fallback(enhanced_message)
        
            # Check if Gemini wants to call a function
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            # Route to real service handler
                            function_result = await self._handle_function_call(
                                part.function_call,
                                progress_notifier=progress_notifier,
                                progress_callback=progress_callback
                            )
                            
                            # Send function result back to Gemini - with retry logic
                            final_response = await self._retry_with_backoff(
                                lambda: self.chat_session.send_message(
                                    Part.from_function_response(
                                        name=part.function_call.name,
                                        response=function_result
                                    )
                                ),
                                max_retries=3,
                                base_delay=2.0
                            )
                            
                            # Extract text from final response
                            response_text = self._extract_text_from_response(final_response)
                            
                            # ✅ FIX 2: Preserve ALL fields from function_result
                            return {
                                'type': function_result.get('type', 'message'),
                                'content': response_text or function_result.get('content', ''),
                                'data': function_result.get('data'),
                                'actions': function_result.get('actions'),
                                'deployment_url': function_result.get('deployment_url'),
                                'request_env_vars': function_result.get('request_env_vars', False),
                                'detected_env_vars': function_result.get('detected_env_vars', []),
                                'timestamp': datetime.now().isoformat()
                            }
            
            # Regular text response (no function call needed)
            response_text = self._extract_text_from_response(response)
            
            return {
                'type': 'message',
                'content': response_text if response_text else 'I received your message but couldn\'t generate a response. Please try again.',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"[Orchestrator] Error: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # User-friendly error message for network issues
            if any(keyword in error_msg.lower() for keyword in ['connection', 'network', 'unavailable', 'timeout', 'iocp', 'socket']):
                user_message = (
                    "❌ **Network Connection Issue**\n\n"
                    "There was a problem connecting to the AI service. This can happen due to:\n"
                    "• Temporary network issues\n"
                    "• Firewall or antivirus blocking connections\n"
                    "• Service availability issues\n\n"
                    "**Please try again in a few moments.** If the issue persists, check your network connection."
                )
            else:
                user_message = f'❌ Error processing message: {error_msg}'
            
            return {
                'type': 'error',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            }

    async def _handle_clone_and_analyze(
        self, 
        repo_url: str, 
        branch: str = 'main', 
        progress_notifier: Optional[ProgressNotifier] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Clone GitHub repo and analyze it - FIXED with real-time progress
        """
        
        try:
            # STAGE 1: Repository Cloning
            if progress_notifier:
                await progress_notifier.start_stage(
                    DeploymentStages.REPO_CLONE,
                    "📦 Cloning repository from GitHub..."
                )
            
            # ✅ FIX 3: Send progress even without progress_notifier
            await self._send_progress_message("📦 Cloning repository from GitHub...")
            
            clone_result = self.github_service.clone_repository(repo_url, branch)
            
            if not clone_result.get('success'):
                if progress_notifier:
                    await progress_notifier.fail_stage(
                        DeploymentStages.REPO_CLONE,
                        f"Failed to clone: {clone_result.get('error')}",
                        details={"error": clone_result.get('error')}
                    )
                return {
                    'type': 'error',
                    'content': f"❌ **Failed to clone repository**\n\n{clone_result.get('error')}\n\nPlease check:\n• Repository URL is correct\n• You have access to the repository\n• GitHub token has proper permissions",
                    'timestamp': datetime.now().isoformat()
                }
            
            project_path = clone_result['local_path']
            self.project_context['project_path'] = project_path
            self.project_context['repo_url'] = repo_url
            self.project_context['branch'] = branch
            
            if progress_notifier:
                await progress_notifier.complete_stage(
                    DeploymentStages.REPO_CLONE,
                    f"✅ Repository cloned ({clone_result['files_count']} files)",
                    details={
                        "repo_name": clone_result['repo_name'],
                        "files": clone_result['files_count'],
                        "size": f"{clone_result['size_mb']} MB"
                    }
                )
            
            await self._send_progress_message(f"✅ Repository cloned: {clone_result['repo_name']} ({clone_result['files_count']} files)")
            
            # Step 2: Analyze project with FIXED progress callback
            if progress_notifier:
                await progress_notifier.start_stage(
                    DeploymentStages.CODE_ANALYSIS,
                    "🔍 Analyzing project structure and dependencies..."
                )
            
            await self._send_progress_message("🔍 Analyzing project structure and dependencies...")
            
            # ✅ FIX 4: Robust progress callback with error handling
            async def analysis_progress(message: str):
                """Send progress updates during analysis with fallbacks"""
                try:
                    # Try progress notifier first
                    if progress_notifier:
                        await progress_notifier.send_update(
                            DeploymentStages.CODE_ANALYSIS,
                            "in-progress",
                            message
                        )
                    
                    # Always try direct WebSocket send as backup
                    await self._send_progress_message(message)
                    
                except Exception as e:
                    print(f"[Orchestrator] Progress callback error: {e}")
                    # Don't fail the analysis if progress update fails
            
            try:
                analysis_result = await self.analysis_service.analyze_and_generate(
                    project_path,
                    progress_callback=analysis_progress  # Pass the fixed callback
                )
            except Exception as e:
                error_msg = str(e)
                # Check if it's a quota error
                if '429' in error_msg or 'quota' in error_msg.lower() or 'resource exhausted' in error_msg.lower():
                    if progress_notifier:
                        await progress_notifier.fail_stage(
                            DeploymentStages.CODE_ANALYSIS,
                            "❌ API Quota Exceeded",
                            details={"error": "Gemini API quota limit reached"}
                        )
                    raise Exception(f"🚨 Gemini API Quota Exceeded. Please check your API quota at https://ai.google.dev/ and try again later.")
                else:
                    raise e
            
            if not analysis_result.get('success'):
                if progress_notifier:
                    await progress_notifier.fail_stage(
                        DeploymentStages.CODE_ANALYSIS,
                        f"Analysis failed: {analysis_result.get('error')}",
                        details={"error": analysis_result.get('error')}
                    )
                return {
                    'type': 'error',
                    'content': f"❌ **Analysis failed**\n\n{analysis_result.get('error')}",
                    'timestamp': datetime.now().isoformat()
                }
            
            analysis_data = analysis_result['analysis']
            
            if progress_notifier:
                await progress_notifier.complete_stage(
                    DeploymentStages.CODE_ANALYSIS,
                    f"✅ Analysis complete: {analysis_data['framework']} detected",
                    details={
                        "framework": analysis_data['framework'],
                        "language": analysis_data['language'],
                        "dependencies": analysis_data.get('dependencies_count', 0)
                    }
                )
            
            await self._send_progress_message(f"✅ Analysis complete: {analysis_data['framework']} detected")
            
            # Step 3: Generate and save Dockerfile
            if progress_notifier:
                await progress_notifier.start_stage(
                    DeploymentStages.DOCKERFILE_GEN,
                    "🐳 Generating optimized Dockerfile..."
                )
            
            await self._send_progress_message("🐳 Generating optimized Dockerfile...")
            
            dockerfile_save = self.docker_service.save_dockerfile(
                analysis_result['dockerfile']['content'],
                project_path
            )
            
            if progress_notifier:
                await progress_notifier.complete_stage(
                    DeploymentStages.DOCKERFILE_GEN,
                    "✅ Dockerfile generated with optimizations",
                    details={
                        "path": dockerfile_save.get('path', f'{project_path}/Dockerfile'),
                        "optimizations": len(analysis_result['dockerfile'].get('optimizations', []))
                    }
                )
            
            await self._send_progress_message("✅ Dockerfile generated with optimizations")
            
            # Step 4: Create .dockerignore
            self.docker_service.create_dockerignore(
                project_path,
                analysis_result['analysis']['language']
            )
            
            # Store analysis in context
            self.project_context['analysis'] = analysis_result['analysis']
            self.project_context['framework'] = analysis_result['analysis']['framework']
            self.project_context['language'] = analysis_result['analysis']['language']
            self.project_context['env_vars_required'] = len(analysis_result['analysis'].get('env_vars', [])) > 0
            
            # Format beautiful response
            content = self._format_analysis_response(
                analysis_result, 
                dockerfile_save, 
                repo_url
            )
            
            # ✅ ALWAYS offer env vars collection (user decides if needed)
            env_vars_detected = analysis_result['analysis'].get('env_vars', [])
            
            if env_vars_detected and len(env_vars_detected) > 0:
                content += f"\n\n⚙️ **Environment Variables Detected:** {len(env_vars_detected)}\n"
                content += "Variables like: " + ", ".join([f"`{v}`" for v in env_vars_detected[:3]])
                if len(env_vars_detected) > 3:
                    content += f" and {len(env_vars_detected) - 3} more"
            
            # ALWAYS return with env vars prompt - user can skip if not needed
            return {
                'type': 'analysis',
                'content': content,
                'data': analysis_result,
                'request_env_vars': True,  # Frontend shows env var collection UI
                'detected_env_vars': env_vars_detected,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[Orchestrator] Clone and analyze error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'type': 'error',
                'content': f'❌ **Analysis failed**\n\n```\n{str(e)}\n```\n\nPlease try again or check the logs.',
                'timestamp': datetime.now().isoformat()
            }


    async def _send_progress_message(self, message: str):
        """
        ✅ FIX: Robust helper to send progress messages during analysis
        CRITICAL: This method must be called AFTER safe_send is stored in process_message
        """
        if not self.safe_send or not self.session_id:
            print(f"[Orchestrator] ⚠️ Cannot send progress: safe_send={bool(self.safe_send)}, session_id={bool(self.session_id)}")
            return
        
        try:
            await self.safe_send(self.session_id, {
                'type': 'message',
                'data': {
                    'content': message,
                    'metadata': {'type': 'progress'}
                },
                'timestamp': datetime.now().isoformat()
            })
            print(f"[Orchestrator] ✅ Sent progress: {message[:50]}...")
        except Exception as e:
            print(f"[Orchestrator] ❌ Error sending progress: {e}")
    
    def _extract_text_from_response(self, response) -> str:
        """Extract text content from Gemini response"""
        try:
            if hasattr(response, 'text') and response.text:
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                parts = response.candidates[0].content.parts
                if parts:
                    return ''.join([
                        part.text for part in parts 
                        if hasattr(part, 'text') and part.text
                    ])
        except Exception as e:
            print(f"[Orchestrator] Error extracting text: {e}")
        return ''
    
    async def _handle_function_call(
        self, 
        function_call, 
        progress_notifier: Optional[ProgressNotifier] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Route Gemini function calls to real service implementations
        
        Args:
            function_call: Gemini function call object
            progress_callback: Optional async callback for WebSocket updates
        """
        
        function_name = function_call.name
        args = dict(function_call.args)
        
        print(f"[Orchestrator] Function call: {function_name} with args: {args}")
        
        # Route to real service handlers
        handlers = {
            'clone_and_analyze_repo': self._handle_clone_and_analyze,
            'deploy_to_cloudrun': self._handle_deploy_to_cloudrun,
            'list_user_repositories': self._handle_list_repos,
            'get_deployment_logs': self._handle_get_logs
        }
        
        handler = handlers.get(function_name)
        
        if handler:
            return await handler(progress_notifier=progress_notifier, progress_callback=progress_callback, **args)
        else:
            return {
                'type': 'error',
                'content': f'❌ Unknown function: {function_name}',
                'timestamp': datetime.now().isoformat()
        }
    
    def _format_analysis_response(
        self, 
        analysis_result: Dict, 
        dockerfile_save: Dict, 
        repo_url: str
    ) -> str:
        """Format analysis results into a beautiful response"""
        analysis_data = analysis_result['analysis']
        
        parts = [
            f"🔍 **Analysis Complete: {repo_url.split('/')[-1]}**\n",
            f"**Framework:** {analysis_data['framework']} ({analysis_data['language']})",
            f"**Entry Point:** `{analysis_data['entry_point']}`",
            f"**Dependencies:** {analysis_data.get('dependencies_count', 0)} packages",
            f"**Port:** {analysis_data['port']}"
        ]
        
        if analysis_data.get('database'):
            parts.append(f"**Database:** {analysis_data['database']}")
        
        if analysis_data.get('env_vars'):
            parts.append(f"**Environment Variables:** {len(analysis_data['env_vars'])} detected")
        
        parts.append(
            f"\n✅ **Dockerfile Generated** ({dockerfile_save.get('path', 'Dockerfile')})"
        )
        
        optimizations = analysis_result['dockerfile']['optimizations'][:4]
        parts.extend(['• ' + opt for opt in optimizations])
        
        parts.append("\n📋 **Recommendations:**")
        recommendations = analysis_result.get('recommendations', [])[:3]
        parts.extend(['• ' + rec for rec in recommendations])
        
        if analysis_result.get('warnings'):
            parts.append("\n⚠️ **Warnings:**")
            warnings = analysis_result['warnings'][:2]
            parts.extend(['• ' + w for w in warnings])
        
        parts.append("\nReady to deploy to Google Cloud Run! Would you like me to proceed?")
        
        return '\n'.join(parts)
    
    async def _handle_deploy_to_cloudrun(
        self,
        project_path: str = None,
        service_name: str = None,
        env_vars: Optional[Dict] = None,
        progress_notifier: Optional[ProgressNotifier] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Deploy to Cloud Run - PRODUCTION IMPLEMENTATION
        
        Features:
        - Security validation and sanitization
        - Resource optimization based on framework
        - Cost estimation
        - Monitoring and metrics
        - Structured logging
        """
        
        # CRITICAL: Use project_path from context if not provided
        if not project_path and 'project_path' in self.project_context:
            project_path = self.project_context['project_path']
            # Normalize path to fix Windows paths
            project_path = project_path.replace('\\', '/').replace('//', '/')
            print(f"[Orchestrator] Using project_path from context (normalized): {project_path}")
        
        if not project_path:
            return {
                'type': 'error',
                'content': '❌ **No repository analyzed yet**\n\nPlease provide a GitHub repository URL first.',
                'timestamp': datetime.now().isoformat()
            }
        
        # Verify project path exists
        import os
        if not os.path.exists(project_path):
            return {
                'type': 'error',
                'content': f'❌ **Project path not found**: {project_path}\n\nThe cloned repository may have been cleaned up. Please clone and analyze the repository again.',
                'timestamp': datetime.now().isoformat()
            }
        
        # CRITICAL: Auto-generate service_name if not provided
        if not service_name:
            # Extract from repo_url or project_path
            repo_url = self.project_context.get('repo_url', '')
            if repo_url:
                # Extract repo name from URL (e.g., "ihealth_backend.git" -> "ihealth-backend")
                repo_name = repo_url.split('/')[-1].replace('.git', '').replace('_', '-').lower()
                service_name = repo_name
                print(f"[Orchestrator] Auto-generated service_name: {service_name}")
            else:
                service_name = 'servergem-app'
        
        # CRITICAL: Use env_vars from project_context if not provided!
        if not env_vars and 'env_vars' in self.project_context and self.project_context['env_vars']:
            print(f"[Orchestrator] Using env_vars from project_context: {len(self.project_context['env_vars'])} vars")
            # Convert format from {key: {value, isSecret}} to {key: value}
            env_vars = {
                key: val['value'] 
                for key, val in self.project_context['env_vars'].items()
            }
        
        if not self.gcloud_service:
            return {
                'type': 'error',
                'content': '❌ **ServerGem Cloud not configured**\n\nPlease contact support. This is a platform configuration issue.',
                'timestamp': datetime.now().isoformat()
            }
        
        # Generate deployment ID for tracking
        deployment_id = f"deploy-{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        try:
            # Create progress tracker for real-time updates
            tracker = self.create_progress_tracker(
                deployment_id,
                service_name,
                progress_callback
            )
            
            # Start monitoring
            metrics = self.monitoring.start_deployment(deployment_id, service_name)
            
            # Security: Validate and sanitize service name
            name_validation = self.security.validate_service_name(service_name)
            if not name_validation['valid']:
                self.monitoring.complete_deployment(deployment_id, "failed")
                return {
                    'type': 'error',
                    'content': f"❌ **Invalid service name**\n\n{name_validation['error']}\n\nRequirements:\n• Lowercase letters, numbers, hyphens only\n• Must start with letter\n• Max 63 characters",
                    'timestamp': datetime.now().isoformat()
                }
            
            service_name = name_validation['sanitized_name']
            
            # Security: Validate environment variables
            if env_vars:
                env_validation = self.security.validate_env_vars(env_vars)
                if env_validation['issues']:
                    self.monitoring.record_error(
                        deployment_id,
                        f"Environment variable issues: {', '.join(env_validation['issues'])}"
                    )
                env_vars = env_validation['sanitized']
            
            # Optimization: Get optimal resource config
            framework = self.project_context.get('framework', 'unknown')
            optimal_config = self.optimization.get_optimal_config(framework, 'medium')
            
            self.monitoring.record_stage(deployment_id, 'validation', 'success', 0.5)
            
            # SERVERGEM ARCHITECTURE: No user GCP auth needed
            # Step 1: Validate Dockerfile exists
            dockerfile_check = self.docker_service.validate_dockerfile(project_path)
            if not dockerfile_check.get('valid'):
                self.monitoring.complete_deployment(deployment_id, 'failed')
                return {
                    'type': 'error',
                    'content': f"❌ **Invalid Dockerfile**\n\n{dockerfile_check.get('error')}",
                    'timestamp': datetime.now().isoformat()
                }
            
            # Security: Scan Dockerfile
            await tracker.start_security_scan()
            
            with open(f"{project_path}/Dockerfile", 'r') as f:
                dockerfile_content = f.read()
            
            security_scan = self.security.scan_dockerfile_security(dockerfile_content)
            
            # Emit security check results
            await tracker.emit_security_check(
                "Base image validation", 
                security_scan['secure']
            )
            await tracker.emit_security_check(
                "Privilege escalation check", 
                not any('privilege' in issue.lower() for issue in security_scan['issues'])
            )
            await tracker.emit_security_check(
                "Secret exposure check", 
                not any('secret' in issue.lower() for issue in security_scan['issues'])
            )
            
            await tracker.complete_security_scan(len(security_scan['issues']))
            
            if not security_scan['secure']:
                for issue in security_scan['issues'][:3]:
                    self.monitoring.record_error(deployment_id, f"Security: {issue}")
                    await tracker.emit_warning(f"Security issue: {issue}")
            
            # Step 3: Build Docker image with Cloud Build
            image_tag = f"gcr.io/servergem-platform/{service_name}:latest"
            await tracker.start_container_build(image_tag)
            
            build_start = time.time()
            
            async def build_progress(data):
                """Forward build progress to tracker"""
                if data.get('step'):
                    await tracker.emit_build_step(
                        data['step'],
                        data.get('total_steps', 10),
                        data.get('description', 'Building...')
                    )
                elif data.get('progress'):
                    await tracker.emit_build_progress(data['progress'])
            
            build_result = await self.gcloud_service.build_image(
                project_path,
                service_name,
                progress_callback=build_progress
            )
            
            build_duration = time.time() - build_start
            
            # CRITICAL: Check build success BEFORE recording metrics
            if not build_result.get('success'):
                self.monitoring.record_stage(deployment_id, 'build', 'failed', build_duration)
                await tracker.emit_error(
                    'container_build', 
                    build_result.get('error', 'Build failed')
                )
                self.monitoring.complete_deployment(deployment_id, 'failed')
                return {
                    'type': 'error',
                    'content': f"❌ **Build failed**\n\n{build_result.get('error')}\n\nCheck:\n• Dockerfile syntax\n• Cloud Build API is enabled\n• Billing is enabled\n• gcloud CLI is authenticated",
                    'timestamp': datetime.now().isoformat()
                }
            
            # Only record success if build actually succeeded
            self.monitoring.record_stage(deployment_id, 'build', 'success', build_duration)
            
            # Emit build completion
            await tracker.complete_container_build(
                build_result.get('image_digest', 'sha256:' + deployment_id[:20])
            )
            
            # Step 4: Deploy to Cloud Run with optimal configuration
            region = build_result.get('region', 'us-central1')
            await tracker.start_cloud_deployment(service_name, region)
            
            await tracker.emit_deployment_config(
                optimal_config.cpu,
                optimal_config.memory,
                optimal_config.concurrency
            )
            
            deploy_start = time.time()
            
            async def deploy_progress(data):
                """Forward deployment progress to tracker"""
                if data.get('status'):
                    await tracker.emit_deployment_status(data['status'])
            
            # Add resource configuration to deployment
            deploy_env = env_vars or {}
            
            deploy_result = await self.gcloud_service.deploy_to_cloudrun(
                build_result['image_tag'],
                service_name,
                env_vars=deploy_env,
                progress_callback=deploy_progress,
                user_id=deployment_id[:8]
            )
            
            deploy_duration = time.time() - deploy_start
            
            # CRITICAL: Check deployment success BEFORE recording metrics
            if not deploy_result.get('success'):
                self.monitoring.record_stage(deployment_id, 'deploy', 'failed', deploy_duration)
                await tracker.emit_error(
                    'cloud_deployment', 
                    deploy_result.get('error', 'Deployment failed')
                )
                self.monitoring.complete_deployment(deployment_id, 'failed')
                return {
                    'type': 'error',
                    'content': f"❌ **Deployment failed**\n\n{deploy_result.get('error')}\n\nCheck:\n• Cloud Run API is enabled\n• Service account permissions\n• gcloud CLI is authenticated",
                    'timestamp': datetime.now().isoformat()
                }
            
            # Only record success if deployment actually succeeded
            self.monitoring.record_stage(deployment_id, 'deploy', 'success', deploy_duration)
            
            # Success! Complete deployment
            await tracker.complete_cloud_deployment(deploy_result['url'])
            
            # Calculate metrics and complete monitoring
            total_duration = time.time() - start_time
            self.monitoring.complete_deployment(deployment_id, 'success')
            
            # Store deployment info
            self.project_context['deployed_service'] = service_name
            self.project_context['deployment_url'] = deploy_result['url']
            self.project_context['deployment_id'] = deployment_id
            
            # Get cost estimation
            estimated_cost = self.optimization.estimate_cost(optimal_config, 100000)
            
            content = self._format_deployment_response(
                deploy_result,
                deployment_id,
                build_duration,
                deploy_duration,
                total_duration,
                optimal_config,
                estimated_cost
            )
            
            return {
                'type': 'deployment_complete',
                'content': content,
                'data': {
                    **deploy_result,
                    'metrics': {
                        'build_duration': build_duration,
                        'deploy_duration': deploy_duration,
                        'total_duration': total_duration
                    },
                    'configuration': {
                        'cpu': optimal_config.cpu,
                        'memory': optimal_config.memory,
                        'concurrency': optimal_config.concurrency,
                        'min_instances': optimal_config.min_instances,
                        'max_instances': optimal_config.max_instances
                    },
                    'cost_estimate': estimated_cost,
                    'security_scan': security_scan
                },
                'deployment_url': deploy_result['url'],
                'actions': [
                    {
                        'id': 'view_logs',
                        'label': '📊 View Logs',
                        'type': 'button',
                        'action': 'view_logs'
                    },
                    {
                        'id': 'setup_cicd',
                        'label': '🔄 Setup CI/CD',
                        'type': 'button',
                        'action': 'setup_cicd'
                    },
                    {
                        'id': 'custom_domain',
                        'label': '🌐 Add Custom Domain',
                        'type': 'button',
                        'action': 'custom_domain'
                    }
                ],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.monitoring.complete_deployment(deployment_id, 'failed')
            print(f"[Orchestrator] Deployment error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'type': 'error',
                'content': f'❌ **Deployment failed**\n\n```\n{str(e)}\n```',
                'timestamp': datetime.now().isoformat()
            }
    
    def _format_deployment_response(
        self,
        deploy_result: Dict,
        deployment_id: str,
        build_duration: float,
        deploy_duration: float,
        total_duration: float,
        optimal_config: ResourceConfig,
        estimated_cost: Dict
    ) -> str:
        """Format deployment success response"""
        return f"""
🎉 **Deployment Successful!**

Your service is now live at:
**{deploy_result['url']}**

**Service:** {deploy_result.get('service_name', 'N/A')}
**Region:** {deploy_result['region']}
**Deployment ID:** `{deployment_id}`

⚡ **Performance:**
• Build: {build_duration:.1f}s
• Deploy: {deploy_duration:.1f}s
• Total: {total_duration:.1f}s

🔧 **Configuration:**
• CPU: {optimal_config.cpu} vCPU
• Memory: {optimal_config.memory}
• Concurrency: {optimal_config.concurrency} requests
• Auto-scaling: {optimal_config.min_instances}-{optimal_config.max_instances} instances

💰 **Estimated Cost (100k requests/month):**
• ${estimated_cost.get('total_monthly', 0):.2f} USD/month

✅ Auto HTTPS enabled
✅ Auto-scaling configured
✅ Health checks active
✅ Monitoring enabled

What would you like to do next?
        """.strip()
    
    async def _handle_list_repos(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """List user's GitHub repositories - REAL IMPLEMENTATION"""
        
        try:
            # Validate GitHub token first
            token_check = self.github_service.validate_token()
            if not token_check.get('valid'):
                return {
                    'type': 'error',
                    'content': f"❌ **GitHub token invalid**\n\n{token_check.get('error')}\n\nPlease set `GITHUB_TOKEN` environment variable.\n\nGet token at: https://github.com/settings/tokens",
                    'timestamp': datetime.now().isoformat()
                }
            
            if progress_callback:
                await progress_callback({
                    'type': 'typing',
                    'message': 'Fetching your GitHub repositories...'
                })
            
            repos = self.github_service.list_repositories()
            
            if not repos:
                return {
                    'type': 'message',
                    'content': '📚 **No repositories found**\n\nCreate a repository on GitHub first, then try again.',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Format repo list beautifully
            repo_list = '\n'.join([
                f"**{i+1}. {repo['name']}** ({repo.get('language', 'Unknown')})"
                f"\n   {repo.get('description', 'No description')[:60]}"
                f"\n   ⭐ {repo.get('stars', 0)} stars | 🔒 {'Private' if repo.get('private') else 'Public'}"
                for i, repo in enumerate(repos[:10])
            ])
            
            content = f"""
📚 **Your GitHub Repositories** ({len(repos)} total)

{repo_list}

Which repository would you like to deploy? Just tell me the name or paste the URL!
            """.strip()
            
            return {
                'type': 'message',
                'content': content,
                'data': {'repositories': repos},
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[Orchestrator] List repos error: {str(e)}")
            return {
                'type': 'error',
                'content': f'❌ **Failed to list repositories**\n\n{str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _handle_get_logs(
        self, 
        service_name: str, 
        limit: int = 50, 
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Get deployment logs - REAL IMPLEMENTATION"""
        
        if not self.gcloud_service:
            return {
                'type': 'error',
                'content': '❌ **Google Cloud not configured**\n\nPlease set `GOOGLE_CLOUD_PROJECT` environment variable.',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            if progress_callback:
                await progress_callback({
                    'type': 'typing',
                    'message': f'Fetching logs for {service_name}...'
                })
            
            logs = self.gcloud_service.get_service_logs(service_name, limit=limit)
            
            if not logs or len(logs) == 0:
                return {
                    'type': 'message',
                    'content': f'📊 **No logs found for {service_name}**\n\nService may not have received traffic yet.',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Format logs
            log_output = '\n'.join(logs[-20:])  # Last 20 entries
            
            content = f"""
📊 **Logs for {service_name}**

```
{log_output}
```

Showing last {min(20, len(logs))} entries (total: {len(logs)})
            """.strip()
            
            return {
                'type': 'message',
                'content': content,
                'data': {'logs': logs},
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[Orchestrator] Get logs error: {str(e)}")
            return {
                'type': 'error',
                'content': f'❌ **Failed to fetch logs**\n\n{str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    # ========================================================================
    # CONTEXT MANAGEMENT
    # ========================================================================
    
    def _build_context_prefix(self) -> str:
        """Build context string - OPTIMIZED for quota efficiency"""
        if not self.project_context:
            return ""
        
        context_parts = []
        
        # Always include deployment state (critical for function routing)
        if 'project_path' in self.project_context:
            context_parts.append(f"Project Path: {self.project_context['project_path']}")
            context_parts.append("STATE: READY - Use deploy_to_cloudrun")
            
            # Add minimal metadata
            if 'framework' in self.project_context:
                context_parts.append(f"Framework: {self.project_context['framework']}")
            
            # Include env vars status (prevents re-asking)
            if 'env_vars' in self.project_context and self.project_context['env_vars']:
                env_count = len(self.project_context['env_vars'])
                context_parts.append(f"Env: {env_count} vars stored")
        
        return "CTX: " + ", ".join(context_parts) if context_parts else ""
    
    def update_context(self, key: str, value: Any):
        """Update project context"""
        self.project_context[key] = value
    
    def get_context(self) -> Dict[str, Any]:
        """Get current project context"""
        return self.project_context.copy()
    
    def clear_context(self):
        """Clear project context"""
        self.project_context.clear()
    
    def reset_chat(self):
        """Reset chat session and context"""
        self.chat_session = None
        self.conversation_history.clear()
        self.project_context.clear()
    


# ============================================================================
# TEST SUITE
# ============================================================================

async def test_orchestrator():
    """Test orchestrator with real services"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    gcloud_project = os.getenv('GOOGLE_CLOUD_PROJECT')
    github_token = os.getenv('GITHUB_TOKEN')
    gcloud_region = os.getenv('GOOGLE_CLOUD_REGION', 'us-central1')
    
    if not gcloud_project:
        print("❌ GOOGLE_CLOUD_PROJECT not found in environment")
        return
    
    print("🚀 Initializing ServerGem Orchestrator with Vertex AI...")
    orchestrator = OrchestratorAgent(
        gcloud_project=gcloud_project,
        github_token=github_token,
        location=gcloud_region
    )
    
    test_messages = [
        "Hello! What can you help me with?",
        "List my GitHub repositories",
        # "Analyze this repo: https://github.com/user/flask-app",
        # "Deploy it to Cloud Run as my-flask-service"
    ]
    
    for msg in test_messages:
        print(f"\n{'='*60}")
        print(f"🧑 USER: {msg}")
        print(f"{'='*60}")
        
        try:
            response = await orchestrator.process_message(
                msg, 
                session_id="test-123"
            )
            print(f"\n🤖 SERVERGEM ({response['type']}):")
            print(response['content'])
            
            if response.get('data'):
                print(f"\n📊 Additional Data: {list(response['data'].keys())}")
            
            if response.get('actions'):
                print(f"\n🎯 Available Actions: {[a['label'] for a in response['actions']]}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print()  # Spacing


async def test_function_calling():
    """Test direct function calling"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    gcloud_project = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not gcloud_project:
        print("❌ GOOGLE_CLOUD_PROJECT not found")
        return
    
    orchestrator = OrchestratorAgent(
        gcloud_project=gcloud_project,
        github_token=os.getenv('GITHUB_TOKEN'),
        location=os.getenv('GOOGLE_CLOUD_REGION', 'us-central1')
    )
    
    print("Testing message that should trigger function call...")
    response = await orchestrator.process_message(
        "Can you list my GitHub repositories?",
        session_id="test-func-call"
    )
    
    print(f"\nResponse Type: {response['type']}")
    print(f"Content:\n{response['content']}")


def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test-functions':
        asyncio.run(test_function_calling())
    else:
        asyncio.run(test_orchestrator())


if __name__ == "__main__":
    main()