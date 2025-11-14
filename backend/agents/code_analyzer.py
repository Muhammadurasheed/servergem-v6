"""
Code Analyzer Agent - Framework and dependency detection
"""

import os
import json
import re
import asyncio  
from pathlib import Path
from typing import Dict, List, Optional, Callable 
import vertexai
from vertexai.generative_models import GenerativeModel


class CodeAnalyzerAgent:
    """
    Analyzes codebases using Vertex AI Gemini for intelligent framework detection
    and dependency analysis with automatic fallback to Gemini API on quota exhaustion.
    """
    
    def __init__(
        self, 
        gcloud_project: str, 
        location: str = 'us-central1',
        gemini_api_key: Optional[str] = None
    ):
        self.gemini_api_key = gemini_api_key
        self.use_vertex_ai = bool(gcloud_project)
        self.gcloud_project = gcloud_project
        
        print(f"[CodeAnalyzer] Initialization:")
        print(f"  - Vertex AI: {self.use_vertex_ai} (project: {gcloud_project})")
        print(f"  - Gemini API key available: {bool(gemini_api_key)}")
        print(f"  - Fallback ready: {self.use_vertex_ai and bool(gemini_api_key)}")
        
        if self.use_vertex_ai:
            vertexai.init(project=gcloud_project, location=location)
            self.model = GenerativeModel('gemini-2.0-flash-exp')
        else:
            # Using Gemini API directly
            import google.generativeai as genai
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    async def analyze_project(self, project_path: str, progress_notifier=None, progress_callback=None) -> Dict:
        """Analyze project structure and configuration with real-time progress updates"""
        
        project_path = Path(project_path)
        
        if progress_callback:
            await progress_callback("🔍 Analyzing project structure...")
            await asyncio.sleep(0)  # ✅ Force event loop flush
        if progress_notifier:
            await progress_notifier.start_stage(
                "code_analysis",
                "🔍 Analyzing project structure and dependencies..."
            )
        
        if not project_path.exists():
            return {'error': 'Project path does not exist'}
        
        # Gather file information
        file_structure = self._scan_directory(project_path)
        
        # ✅ PHASE 1.1: Progress - Scanning files WITH flush
        if progress_callback:
            await progress_callback(f"📂 Scanned {len(file_structure['files'])} files")
            await asyncio.sleep(0)  # ✅ Force event loop flush
        if progress_notifier:
            await progress_notifier.update_progress(
                "code_analysis",
                f"📂 Scanned {len(file_structure['files'])} files",
                25
            )
        
        # Use Gemini to intelligently analyze the project
        analysis_prompt = self._build_analysis_prompt(file_structure, project_path)
        
        # ✅ PHASE 1.1: Progress - Analyzing with AI WITH flush
        if progress_callback:
            await progress_callback("🤖 AI analyzing code structure...")
            await asyncio.sleep(0)  # ✅ Force event loop flush
        if progress_notifier:
            await progress_notifier.update_progress(
                "code_analysis",
                "🤖 Using AI to detect framework and dependencies...",
                30
            )
        
        try:
            # Try with current model (Vertex AI or Gemini API)
            if self.use_vertex_ai:
                response = await self.model.generate_content_async(analysis_prompt)
            else:
                # Gemini API uses synchronous method
                response = self.model.generate_content(analysis_prompt)
            
            # Properly extract text from Gemini response
            response_text = None
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                parts = response.candidates[0].content.parts
                if parts:
                    response_text = ''.join([part.text for part in parts if hasattr(part, 'text')])
            
            if not response_text:
                print("[CodeAnalyzer] No text in Gemini response, using fallback")
                return self._fallback_analysis(project_path, file_structure)
            
            # Extract JSON from response (handle markdown code blocks)
            response_text = response_text.strip()
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            analysis = json.loads(response_text)
            
            # Enhance with static analysis
            analysis['env_vars'] = self._extract_env_vars(project_path)
            analysis['dockerfile_exists'] = (project_path / 'Dockerfile').exists()
            
            # ✅ PHASE 1.1: Progress - Analysis complete WITH flush
            if progress_callback:
                await progress_callback(f"✅ Detected {analysis.get('framework', 'unknown')} framework")
                await asyncio.sleep(0)  # ✅ Force event loop flush
            if progress_notifier:
                await progress_notifier.complete_stage(
                    "code_analysis",
                    f"✅ Project analyzed: {analysis.get('framework', 'unknown')} application",
                    details={
                        'framework': analysis.get('framework', 'unknown'),
                        'language': analysis.get('language', 'unknown'),
                        'dependencies': len(analysis.get('dependencies', [])),
                        'env_vars': len(analysis.get('env_vars', []))
                    }
                )
            
            return analysis
        
        except Exception as e:
            error_msg = str(e)
            print(f"[CodeAnalyzer] Error: {error_msg}")
            
            # ✅ Check for quota/resource exhausted error
            from google.api_core.exceptions import ResourceExhausted
            is_quota_error = isinstance(e, ResourceExhausted) or any(keyword in error_msg.lower() for keyword in [
                'resource exhausted', '429', 'quota', 'rate limit'
            ])
            
            if is_quota_error and self.use_vertex_ai and self.gemini_api_key:
                print(f"[CodeAnalyzer] ⚠️ Quota error detected, activating fallback to Gemini API")
                if progress_callback:
                    await progress_callback("⚠️ Quota exhausted. Switching to backup AI service...")
                    await asyncio.sleep(0)
                
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=self.gemini_api_key)
                    
                    # ✅ CRITICAL FIX: Use correct model name for v1beta API
                    backup_model = genai.GenerativeModel('gemini-1.5-flash-latest')
                    response = backup_model.generate_content(analysis_prompt)
                    
                    # Switch permanently to Gemini API
                    self.use_vertex_ai = False
                    self.model = backup_model
                    
                    print(f"[CodeAnalyzer] ✅ Successfully switched to Gemini API (gemini-1.5-flash-latest)")
                    if progress_callback:
                        await progress_callback("✅ Using backup AI service - analysis continues...")
                        await asyncio.sleep(0)
                    
                    # Continue with response processing (same code as above)
                    response_text = None
                    if hasattr(response, 'text') and response.text:
                        response_text = response.text
                    elif hasattr(response, 'candidates') and response.candidates:
                        parts = response.candidates[0].content.parts
                        if parts:
                            response_text = ''.join([part.text for part in parts if hasattr(part, 'text')])
                    
                    if not response_text:
                        print("[CodeAnalyzer] No text in Gemini response, using fallback")
                        return self._fallback_analysis(project_path, file_structure)
                    
                    # Extract JSON from response
                    response_text = response_text.strip()
                    if '```json' in response_text:
                        response_text = response_text.split('```json')[1].split('```')[0].strip()
                    elif '```' in response_text:
                        response_text = response_text.split('```')[1].split('```')[0].strip()
                    
                    analysis = json.loads(response_text)
                    analysis['env_vars'] = self._extract_env_vars(project_path)
                    analysis['dockerfile_exists'] = (project_path / 'Dockerfile').exists()
                    
                    if progress_callback:
                        await progress_callback(f"✅ Detected {analysis.get('framework', 'unknown')} framework")
                        await asyncio.sleep(0)
                    if progress_notifier:
                        await progress_notifier.complete_stage(
                            "code_analysis",
                            f"✅ Project analyzed: {analysis.get('framework', 'unknown')} application",
                            details={
                                'framework': analysis.get('framework', 'unknown'),
                                'language': analysis.get('language', 'unknown'),
                                'dependencies': len(analysis.get('dependencies', [])),
                                'env_vars': len(analysis.get('env_vars', []))
                            }
                        )
                    
                    return analysis
                    
                except Exception as fallback_err:
                    print(f"[CodeAnalyzer] ❌ Fallback to Gemini API failed: {fallback_err}")
                    # Continue to static fallback analysis
            
            # For other errors or if fallback also failed, use static analysis
            return self._fallback_analysis(project_path, file_structure)
    
    def _scan_directory(self, path: Path, max_depth: int = 3) -> Dict:
        """Scan directory structure (exclude node_modules, venv, etc.)"""
        
        exclude_dirs = {
            'node_modules', 'venv', '__pycache__', '.git', 
            'dist', 'build', 'target', 'vendor'
        }
        
        structure = {
            'files': [],
            'directories': [],
            'config_files': []
        }
        
        config_patterns = [
            'package.json', 'requirements.txt', 'go.mod', 'pom.xml',
            'Gemfile', 'composer.json', '.env', 'Dockerfile',
            'docker-compose.yml', 'app.yaml', 'cloudbuild.yaml'
        ]
        
        for item in path.rglob('*'):
            # Skip excluded directories
            if any(excluded in item.parts for excluded in exclude_dirs):
                continue
            
            if item.is_file():
                rel_path = str(item.relative_to(path))
                structure['files'].append(rel_path)
                
                if item.name in config_patterns:
                    structure['config_files'].append(rel_path)
        
        return structure
    
    def _build_analysis_prompt(self, file_structure: Dict, project_path: Path) -> str:
        """Build analysis prompt for Gemini"""
        
        # Read key configuration files
        config_contents = {}
        for config_file in file_structure['config_files'][:10]:  # Limit to first 10
            try:
                full_path = project_path / config_file
                if full_path.stat().st_size < 50000:  # Only read files < 50KB
                    config_contents[config_file] = full_path.read_text()
            except:
                continue
        
        prompt = f"""
Analyze this software project and return a JSON object with deployment information.

**File Structure:**
{json.dumps(file_structure, indent=2)}

**Configuration Files:**
{json.dumps(config_contents, indent=2)}

**Return JSON in this exact format:**
{{
  "language": "python|nodejs|golang|java|ruby|php",
  "framework": "express|flask|django|fastapi|nextjs|gin|springboot|rails",
  "entry_point": "main file (e.g., app.py, index.js, main.go)",
  "port": 8080,
  "dependencies": [
    {{"name": "package-name", "version": "1.0.0"}}
  ],
  "database": "postgresql|mysql|mongodb|redis|none",
  "build_tool": "npm|pip|go|maven|gradle|bundle",
  "start_command": "command to start the application",
  "recommendations": [
    "deployment recommendation 1",
    "deployment recommendation 2"
  ],
  "warnings": [
    "potential issue 1",
    "potential issue 2"
  ]
}}

Return ONLY valid JSON, no markdown or explanations.
"""
        
        return prompt
    
    def _extract_env_vars(self, project_path: Path) -> List[str]:
        """Extract environment variables from .env files"""
        
        env_vars = []
        env_files = ['.env', '.env.example', '.env.sample']
        
        for env_file in env_files:
            env_path = project_path / env_file
            if env_path.exists():
                try:
                    content = env_path.read_text()
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            var_name = line.split('=')[0].strip()
                            env_vars.append(var_name)
                except:
                    continue
        
        return list(set(env_vars))  # Remove duplicates
    
    def _fallback_analysis(self, project_path: Path, file_structure: Dict) -> Dict:
        """Fallback static analysis if Gemini fails"""
        
        analysis = {
            'language': 'unknown',
            'framework': 'unknown',
            'entry_point': None,
            'port': 8080,
            'dependencies': [],
            'database': None,
            'build_tool': None,
            'start_command': None,
            'env_vars': [],
            'dockerfile_exists': False,
            'recommendations': ['Unable to fully analyze project - manual configuration may be needed'],
            'warnings': ['Automated analysis failed - using fallback detection']
        }
        
        # Basic detection logic
        if 'package.json' in file_structure['config_files']:
            analysis['language'] = 'nodejs'
            analysis['build_tool'] = 'npm'
            try:
                pkg = json.loads((project_path / 'package.json').read_text())
                deps = pkg.get('dependencies', {})
                if 'express' in deps:
                    analysis['framework'] = 'express'
                elif 'next' in deps:
                    analysis['framework'] = 'nextjs'
            except:
                pass
        
        elif 'requirements.txt' in file_structure['config_files']:
            analysis['language'] = 'python'
            analysis['build_tool'] = 'pip'
            
            # Check for Flask/Django/FastAPI
            for py_file in ['app.py', 'main.py', 'manage.py']:
                if py_file in file_structure['files']:
                    analysis['entry_point'] = py_file
                    break
        
        elif 'go.mod' in file_structure['config_files']:
            analysis['language'] = 'golang'
            analysis['build_tool'] = 'go'
            analysis['entry_point'] = 'main.go'
        
        analysis['env_vars'] = self._extract_env_vars(project_path)
        analysis['dockerfile_exists'] = (project_path / 'Dockerfile').exists()
        
        return analysis


# Test analyzer
async def test_analyzer():
    import os
    from dotenv import load_dotenv
    import tempfile
    
    load_dotenv()
    
    gcloud_project = os.getenv('GOOGLE_CLOUD_PROJECT')
    analyzer = CodeAnalyzerAgent(gcloud_project=gcloud_project)
    
    # Create mock Flask project
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    (temp_path / 'app.py').write_text("""
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World'

if __name__ == '__main__':
    app.run(port=5000)
""")
    
    (temp_path / 'requirements.txt').write_text("""
flask==3.0.0
psycopg2==2.9.9
gunicorn==21.2.0
""")
    
    (temp_path / '.env').write_text("""
DATABASE_URL=postgresql://localhost/mydb
SECRET_KEY=mysecret
""")
    
    print("🔍 Analyzing project...\n")
    analysis = await analyzer.analyze_project(temp_dir)
    
    print(json.dumps(analysis, indent=2))
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_analyzer())
