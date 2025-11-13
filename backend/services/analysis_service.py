"""
Analysis Service - Coordinates code analysis workflow
Integrates CodeAnalyzer with real project paths
"""

from pathlib import Path
from typing import Dict
from agents.code_analyzer import CodeAnalyzerAgent
from agents.docker_expert import DockerExpertAgent


class AnalysisService:
    """Orchestrates code analysis and Dockerfile generation"""
    
    def __init__(self, gcloud_project: str, location: str = 'us-central1'):
        self.code_analyzer = CodeAnalyzerAgent(gcloud_project, location)
        self.docker_expert = DockerExpertAgent(gcloud_project, location)
    
    async def analyze_and_generate(self, project_path: str, progress_callback=None, progress_notifier=None) -> Dict:
        """
        Full analysis workflow with real-time progress updates:
        1. Analyze codebase
        2. Generate Dockerfile
        3. Return comprehensive report
        
        ✅ PHASE 1.1: Now accepts progress_notifier for structured updates
        """
        try:
            # ✅ PHASE 1.1: Pass progress_notifier to code analyzer
            print(f"[AnalysisService] Analyzing project at {project_path}")
            if progress_callback:
                await progress_callback("🔍 Starting code analysis...")
                await progress_callback("📂 Scanning project structure...")
            
            analysis = await self.code_analyzer.analyze_project(project_path, progress_notifier=progress_notifier)
            
            # ✅ PHASE 2: Detailed framework detection feedback
            if progress_callback:
                framework = analysis.get('framework', 'application')
                language = analysis.get('language', 'unknown')
                await progress_callback(f"✅ Framework detected: {framework}")
                await progress_callback(f"📝 Language: {language}")
                
                # Report dependencies
                dep_count = len(analysis.get('dependencies', []))
                if dep_count > 0:
                    await progress_callback(f"📦 Found {dep_count} dependencies")
            
            if 'error' in analysis:
                return {
                    'success': False,
                    'error': analysis['error']
                }
            
            # ✅ PHASE 1.1: Pass progress_notifier to docker expert
            print(f"[AnalysisService] Generating Dockerfile for {analysis['framework']}")
            if progress_callback:
                await progress_callback(f"🐳 Starting Dockerfile generation...")
                await progress_callback(f"⚙️  Optimizing for {analysis['framework']} framework...")
            
            dockerfile_result = await self.docker_expert.generate_dockerfile(analysis, progress_notifier=progress_notifier)
            
            if progress_callback:
                await progress_callback("✅ Dockerfile generated successfully!")
                await progress_callback("🔒 Applied security best practices")
                await progress_callback("📦 Multi-stage build configured")
            
            # Step 3: Compile report
            report = {
                'success': True,
                'analysis': {
                    'language': analysis['language'],
                    'framework': analysis['framework'],
                    'entry_point': analysis['entry_point'],
                    'dependencies_count': len(analysis['dependencies']),
                    'database': analysis.get('database'),
                    'port': analysis.get('port'),
                    'env_vars': analysis['env_vars']
                },
                'dockerfile': {
                    'content': dockerfile_result['dockerfile'],
                    'optimizations': dockerfile_result.get('optimizations', []),
                    'explanations': dockerfile_result.get('explanations', [])
                },
                'recommendations': analysis.get('recommendations', []),
                'warnings': analysis.get('warnings', []),
                'next_steps': [
                    'Review the generated Dockerfile',
                    'Configure environment variables',
                    'Set up secrets in Secret Manager',
                    'Deploy to Cloud Run'
                ]
            }
            
            return report
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Analysis failed: {str(e)}'
            }
    
    async def quick_analysis(self, project_path: str) -> Dict:
        """Quick analysis without Dockerfile generation"""
        try:
            analysis = await self.code_analyzer.analyze_project(project_path)
            
            if 'error' in analysis:
                return {'success': False, 'error': analysis['error']}
            
            return {
                'success': True,
                'language': analysis['language'],
                'framework': analysis['framework'],
                'dependencies': len(analysis['dependencies']),
                'database': analysis.get('database'),
                'ready_to_deploy': analysis['language'] != 'unknown'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Quick analysis failed: {str(e)}'
            }
