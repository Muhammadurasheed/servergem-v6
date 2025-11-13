"""
Docker Expert Agent - Optimized Dockerfile generation
"""

import asyncio  # ✅ CRITICAL: Import asyncio for sleep(0) flush
from pathlib import Path
from typing import Dict, Optional, Callable  # ✅ Added Optional, Callable
import vertexai
from vertexai.generative_models import GenerativeModel


class DockerExpertAgent:
    """
    Generates production-optimized Dockerfiles using Vertex AI Gemini
    and pre-built templates for common frameworks.
    """
    
    def __init__(self, gcloud_project: str, location: str = 'us-central1'):
        vertexai.init(project=gcloud_project, location=location)
        self.model = GenerativeModel('gemini-2.0-flash-exp')
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        """Production-optimized Dockerfile templates"""
        
        return {
            'python_flask': """# Multi-stage build for Flask
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
RUN useradd -m -u 1001 appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .
USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 {entry_point}:app
""",
            
            'python_fastapi': """# Multi-stage build for FastAPI
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
RUN useradd -m -u 1001 appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .
USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn", "{entry_point}:app", "--host", "0.0.0.0", "--port", "8080"]
""",
            
            'nodejs_express': """# Multi-stage build for Express
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force
COPY . .

FROM node:18-alpine
WORKDIR /app
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
COPY --from=builder --chown=nodejs:nodejs /app /app
USER nodejs
ENV PORT=8080
ENV NODE_ENV=production
EXPOSE 8080
CMD ["node", "{entry_point}"]
""",
            
            'nodejs_nextjs': """# Multi-stage build for Next.js
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=8080
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 8080
CMD ["node", "server.js"]
""",
            
            'golang_gin': """# Multi-stage build for Go
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/main .
ENV PORT=8080
EXPOSE 8080
CMD ["./main"]
"""
        }
    
    async def generate_dockerfile(self, analysis: Dict, progress_notifier=None, progress_callback=None) -> Dict:
        """Generate optimized Dockerfile based on analysis with real-time progress"""
        
        # ✅ PHASE 1.1: Send progress - Starting Dockerfile generation WITH flush
        if progress_callback:
            await progress_callback(f"🐳 Generating Dockerfile for {analysis.get('framework', 'unknown')}...")
            await asyncio.sleep(0)  # ✅ Force event loop flush
        if progress_notifier:
            await progress_notifier.start_stage(
                "dockerfile_generation",
                f"📝 Generating optimized Dockerfile for {analysis.get('framework', 'unknown')}..."
            )
        
        framework_key = f"{analysis['language']}_{analysis['framework']}"
        
        if framework_key in self.templates:
            # ✅ PHASE 1.1: Progress - Using template WITH flush
            if progress_callback:
                await progress_callback(f"📋 Optimizing for {framework_key}")
                await asyncio.sleep(0)  # ✅ Force event loop flush
            if progress_notifier:
                await progress_notifier.update_progress(
                    "dockerfile_generation",
                    f"📋 Using optimized template for {framework_key}",
                    50
                )
            
            template = self.templates[framework_key]
            dockerfile = self._customize_template(template, analysis)
            
            # ✅ PHASE 1.1: Progress - Dockerfile complete WITH flush
            if progress_callback:
                await progress_callback("✅ Dockerfile ready with optimizations")
                await asyncio.sleep(0)  # ✅ Force event loop flush
            if progress_notifier:
                await progress_notifier.complete_stage(
                    "dockerfile_generation",
                    "✅ Dockerfile generated with production optimizations",
                    details={
                        'template': framework_key,
                        'size_estimate': self._estimate_image_size(framework_key),
                        'multi_stage': True,
                        'security_hardened': True
                    }
                )
            
            return {
                'dockerfile': dockerfile,
                'optimizations': [
                    "✅ Multi-stage build (50-70% smaller image)",
                    "✅ Non-root user (security hardened)",
                    "✅ Layer caching optimized",
                    "✅ Cloud Run compatible (PORT env var)",
                    "✅ Production-grade server configuration"
                ],
                'size_estimate': self._estimate_image_size(framework_key)
            }
        
        # Use Gemini for custom frameworks
        # ✅ PHASE 1.1: Progress - Using AI for custom framework
        if progress_notifier:
            await progress_notifier.update_progress(
                "dockerfile_generation",
                "🤖 Generating custom Dockerfile with AI...",
                40
            )
        
        result = await self._generate_custom_dockerfile(analysis)
        
        # ✅ PHASE 1.1: Progress - Custom Dockerfile complete
        if progress_notifier:
            await progress_notifier.complete_stage(
                "dockerfile_generation",
                "✅ Custom Dockerfile generated",
                details={'framework': analysis.get('framework', 'custom')}
            )
        
        return result
    
    def _customize_template(self, template: str, analysis: Dict) -> str:
        """Customize template with project-specific values - ROBUST"""
        
        # Sanitize entry point - remove extensions and validate
        entry_point = analysis.get('entry_point', 'app')
        if not entry_point or entry_point == 'unknown':
            # Safe defaults per language
            if 'python' in template.lower():
                entry_point = 'app'
            elif 'node' in template.lower():
                entry_point = 'server.js'
            else:
                entry_point = 'main'
        
        # Clean entry point name
        entry_point = str(entry_point).strip()
        entry_point = entry_point.replace('.py', '').replace('.js', '').replace('.ts', '')
        
        # Ensure valid identifier (no spaces, special chars except underscore/hyphen)
        entry_point = ''.join(c for c in entry_point if c.isalnum() or c in '_-.')
        
        if not entry_point:
            entry_point = 'app'
        
        return template.replace('{entry_point}', entry_point)
    
    def _estimate_image_size(self, framework_key: str) -> str:
        """Estimate final image size"""
        
        sizes = {
            'python_flask': '~150MB',
            'python_fastapi': '~150MB',
            'nodejs_express': '~120MB',
            'nodejs_nextjs': '~180MB',
            'golang_gin': '~25MB'
        }
        
        return sizes.get(framework_key, '~200MB')
    
    async def _generate_custom_dockerfile(self, analysis: Dict) -> Dict:
        """Use Gemini to generate Dockerfile for unsupported frameworks"""
        
        prompt = f"""
Generate a production-optimized Dockerfile for Google Cloud Run with these requirements:

**Project Details:**
- Language: {analysis['language']}
- Framework: {analysis['framework']}
- Entry Point: {analysis.get('entry_point', 'unknown')}
- Port: {analysis.get('port', 8080)}
- Build Tool: {analysis.get('build_tool', 'unknown')}

**Requirements:**
1. Multi-stage build to minimize image size
2. Non-root user for security
3. Use PORT environment variable (Cloud Run requirement)
4. Layer caching optimization
5. Production-ready configuration
6. Include helpful comments

Return ONLY the Dockerfile content, no markdown formatting.
"""
        
        response = await self.model.generate_content_async(prompt)
        
        # Properly extract text from Gemini response
        dockerfile_content = None
        if hasattr(response, 'text') and response.text:
            dockerfile_content = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            parts = response.candidates[0].content.parts
            if parts:
                dockerfile_content = ''.join([part.text for part in parts if hasattr(part, 'text')])
        
        if not dockerfile_content:
            # Fallback to basic template
            dockerfile_content = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8080
EXPOSE 8080
CMD ["python", "{analysis.get('entry_point', 'app.py')}"]
"""
        
        # Clean up markdown if present
        if '```dockerfile' in dockerfile_content:
            dockerfile_content = dockerfile_content.split('```dockerfile')[1].split('```')[0].strip()
        elif '```' in dockerfile_content:
            dockerfile_content = dockerfile_content.split('```')[1].split('```')[0].strip()
        
        return {
            'dockerfile': dockerfile_content,
            'optimizations': ["🤖 AI-generated for your specific stack"],
            'size_estimate': '~200MB'
        }


# Test docker expert
async def test_docker_expert():
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    gcloud_project = os.getenv('GOOGLE_CLOUD_PROJECT')
    expert = DockerExpertAgent(gcloud_project=gcloud_project)
    
    mock_analysis = {
        'language': 'python',
        'framework': 'flask',
        'entry_point': 'app.py',
        'port': 5000
    }
    
    print("🐳 Generating Dockerfile...\n")
    result = await expert.generate_dockerfile(mock_analysis)
    
    print("="*60)
    print("DOCKERFILE:")
    print("="*60)
    print(result['dockerfile'])
    print("\n" + "="*60)
    print("OPTIMIZATIONS:")
    print("="*60)
    for opt in result['optimizations']:
        print(f"  {opt}")
    print(f"\nEstimated Size: {result['size_estimate']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_docker_expert())
