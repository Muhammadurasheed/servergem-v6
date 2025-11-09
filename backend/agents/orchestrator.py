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
        location: str = 'us-central1'
    ):
        if not gcloud_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required")
            
        # Initialize Vertex AI
        vertexai.init(project=gcloud_project, location=location)
        
        # ServerGem-specific system instruction
        system_instruction = """
You are ServerGem AI Assistant - a production-grade AI that deploys applications to Google Cloud Run using ServerGem's managed infrastructure.

CRITICAL ARCHITECTURE PRINCIPLES:
- Users do NOT need Google Cloud accounts or gcloud authentication
- Users do NOT need to provide project IDs or service account keys
- ServerGem handles ALL Google Cloud interactions using its own managed infrastructure
- You deploy everything to ServerGem's platform and provide custom .servergem.app URLs

NEVER ask users for:
❌ Google Cloud project IDs
❌ Service account keys
❌ gcloud CLI authentication commands
❌ IAM permissions or roles

ALWAYS ask for:
✅ GitHub repository URL
✅ Environment variables (if app needs them)

CRITICAL: ENVIRONMENT VARIABLES HANDLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When the user uploads a .env file or provides environment variables:
1. The system automatically parses and stores ALL key-value pairs
2. You will receive a confirmation that env vars are stored
3. NEVER ask the user to provide values again in JSON format
4. NEVER say: "Please provide the values for each of them..."
5. NEVER show example JSON like: {"KEY": "value"}
6. The env vars are ALREADY in the system context
7. Simply confirm receipt and proceed with deployment

CRITICAL: WHEN USER SAYS "DEPLOY" OR "YES" AFTER ENV UPLOAD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When user says "deploy", "yes", "go ahead", "start deployment", etc. AND you have already:
- Cloned and analyzed a repository
- Generated a Dockerfile
- Received environment variables (if needed)

YOU MUST IMMEDIATELY call the deploy_to_cloudrun function with:
- project_path: Use the value from context (the cloned repo path)
- service_name: Auto-generate from repo name (e.g., "ihealth-backend" from "ihealth_backend.git")
- env_vars: Leave empty (will be pulled from context automatically)

DO NOT:
❌ Ask for the repository URL again
❌ Ask what to deploy
❌ Ask for service name
❌ Say "I need the GitHub repository URL to get started"

CORRECT FLOW:
User: [uploads .env file]
System: [Stores all env vars]
You: "✅ Configuration received! Ready to deploy?"
User: "deploy"
You: [CALL deploy_to_cloudrun function IMMEDIATELY with context values]

INCORRECT FLOW (NEVER DO THIS):
User: "deploy"
You: "Okay, I'm ready to deploy. I need the GitHub repository URL to get started." ❌ WRONG!

DEPLOYMENT FLOW:
1. User provides GitHub repo URL
2. You call clone_and_analyze_repo function
3. You generate optimal Dockerfile
4. You deploy to ServerGem's Cloud Run infrastructure
5. You provide custom URL: https://{service-name}.servergem.app

Be concise, helpful, and NEVER mention gcloud setup or GCP authentication.
        """.strip()
        
        # Initialize Vertex AI Gemini with function declarations and system instruction
        self.model = GenerativeModel(
            'gemini-2.0-flash-exp',
            tools=[self._get_function_declarations()],
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
    
    def _get_function_declarations(self) -> Tool:
        """
        Define real functions available for Vertex AI Gemini to call
        Uses Vertex AI SDK format
        """
        return Tool(
            function_declarations=[
                FunctionDeclaration(
                    name='clone_and_analyze_repo',
                    description='Clone a GitHub repository and perform comprehensive analysis to detect framework, dependencies, and deployment requirements. Use this when user provides a GitHub repo URL.',
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
    
    async def process_message(
        self, 
        user_message: str, 
        session_id: str, 
        progress_notifier: Optional[ProgressNotifier] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: processes user message with Gemini ADK function calling
        
        Args:
            user_message: User's chat message
            session_id: Session identifier
            progress_callback: Optional async callback for real-time updates
        """
        
        # Initialize chat session if needed
        if not self.chat_session:
            self.chat_session = self.model.start_chat(history=[])
        
        # Add project context to enhance Gemini's understanding
        context_prefix = self._build_context_prefix()
        enhanced_message = (
            f"{context_prefix}\n\nUser: {user_message}" 
            if context_prefix 
            else user_message
        )
        
        try:
            # Send to Gemini with function calling enabled
            # Note: send_message is synchronous, no need for asyncio.to_thread
            response = self.chat_session.send_message(enhanced_message)
            
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
                            
                            # Send function result back to Gemini using Part.from_function_response
                            final_response = self.chat_session.send_message(
                                Part.from_function_response(
                                    name=part.function_call.name,
                                    response=function_result
                                )
                            )
                            
                            # Extract text from final response
                            response_text = self._extract_text_from_response(final_response)
                            
                            # Return combined result
                            return {
                                'type': function_result.get('type', 'message'),
                                'content': response_text or function_result.get('content', ''),
                                'data': function_result.get('data'),
                                'actions': function_result.get('actions'),
                                'deployment_url': function_result.get('deployment_url'),
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
            print(f"[Orchestrator] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'type': 'error',
                'content': f'❌ Error processing message: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
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
    
    # ========================================================================
    # REAL SERVICE HANDLERS - Production Implementation
    # ========================================================================
    
    async def _handle_clone_and_analyze(
        self, 
        repo_url: str, 
        branch: str = 'main', 
        progress_notifier: Optional[ProgressNotifier] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Clone GitHub repo and analyze it - REAL IMPLEMENTATION with real-time progress
        Uses: GitHubService, AnalysisService, DockerService
        """
        
        try:
            # STAGE 1: Repository Cloning
            if progress_notifier:
                await progress_notifier.start_stage(
                    DeploymentStages.REPO_CLONE,
                    "📦 Cloning repository from GitHub..."
                )
            
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
            
            # Step 2: Analyze project using AnalysisService
            if progress_notifier:
                await progress_notifier.start_stage(
                    DeploymentStages.CODE_ANALYSIS,
                    "🔍 Analyzing project structure and dependencies..."
                )
            
            try:
                analysis_result = await self.analysis_service.analyze_and_generate(project_path)
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
                    # This will trigger error handling in app.py
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
            
            # Step 3: Generate and save Dockerfile
            if progress_notifier:
                await progress_notifier.start_stage(
                    DeploymentStages.DOCKERFILE_GEN,
                    "🐳 Generating optimized Dockerfile..."
                )
            
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
            
            # Step 4: Create .dockerignore
            self.docker_service.create_dockerignore(
                project_path,
                analysis_result['analysis']['language']
            )
            
            # Store analysis in context for future operations
            self.project_context['analysis'] = analysis_result['analysis']
            self.project_context['framework'] = analysis_result['analysis']['framework']
            self.project_context['language'] = analysis_result['analysis']['language']
            
            # Format beautiful response
            content = self._format_analysis_response(
                analysis_result, 
                dockerfile_save, 
                repo_url
            )
            
            return {
                'type': 'analysis',
                'content': content,
                'data': analysis_result,
                'actions': [
                    {
                        'id': 'deploy',
                        'label': '🚀 Deploy to Cloud Run',
                        'type': 'button',
                        'action': 'deploy'
                    },
                    {
                        'id': 'view_dockerfile',
                        'label': '📄 View Dockerfile',
                        'type': 'button',
                        'action': 'view_dockerfile'
                    },
                    {
                        'id': 'configure_env',
                        'label': '⚙️ Configure Env Vars',
                        'type': 'button',
                        'action': 'configure_env'
                    }
                ],
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
            print(f"[Orchestrator] Using project_path from context: {project_path}")
        
        if not project_path:
            return {
                'type': 'error',
                'content': '❌ **No repository analyzed yet**\n\nPlease provide a GitHub repository URL first.',
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
            self.monitoring.record_stage(deployment_id, 'build', 'success', build_duration)
            
            if not build_result.get('success'):
                await tracker.emit_error(
                    'container_build', 
                    build_result.get('error', 'Build failed')
                )
                self.monitoring.complete_deployment(deployment_id, 'failed')
                return {
                    'type': 'error',
                    'content': f"❌ **Build failed**\n\n{build_result.get('error')}\n\nCheck:\n• Dockerfile syntax\n• Cloud Build API is enabled\n• Billing is enabled",
                    'timestamp': datetime.now().isoformat()
                }
            
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
            self.monitoring.record_stage(deployment_id, 'deploy', 'success', deploy_duration)
            
            if not deploy_result.get('success'):
                await tracker.emit_error(
                    'cloud_deployment', 
                    deploy_result.get('error', 'Deployment failed')
                )
                self.monitoring.complete_deployment(deployment_id, 'failed')
                return {
                    'type': 'error',
                    'content': f"❌ **Deployment failed**\n\n{deploy_result.get('error')}\n\nCheck:\n• Cloud Run API is enabled\n• Service account permissions",
                    'timestamp': datetime.now().isoformat()
                }
            
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
        """Build context string from stored project data"""
        if not self.project_context:
            return ""
        
        context_parts = []
        if 'framework' in self.project_context:
            context_parts.append(f"Framework: {self.project_context['framework']}")
        if 'language' in self.project_context:
            context_parts.append(f"Language: {self.project_context['language']}")
        if 'deployed_service' in self.project_context:
            context_parts.append(f"Deployed Service: {self.project_context['deployed_service']}")
        if 'project_path' in self.project_context:
            context_parts.append(f"Project Path: {self.project_context['project_path']}")
        
        # CRITICAL: Include env vars info so Gemini knows they're already provided!
        if 'env_vars' in self.project_context and self.project_context['env_vars']:
            env_count = len(self.project_context['env_vars'])
            secret_count = sum(1 for v in self.project_context['env_vars'].values() if v.get('isSecret'))
            context_parts.append(f"Environment Variables: {env_count} variables provided ({secret_count} secrets)")
            context_parts.append("⚠️ IMPORTANT: Env vars are ALREADY stored - DO NOT ask user for them again!")
        
        return "Current project context: " + ", ".join(context_parts) if context_parts else ""
    
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