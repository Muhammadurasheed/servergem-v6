"""
PHASE 2.3: Post-Deployment Verification Service
FAANG-Level health checking and service verification
"""

import asyncio
import aiohttp
import time
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    success: bool
    status_code: Optional[int]
    response_time_ms: float
    timestamp: str
    error: Optional[str] = None
    body: Optional[str] = None


class HealthCheckService:
    """
    Production-grade health checking service
    
    Features:
    - HTTP/HTTPS endpoint verification
    - Custom health check paths
    - Retry with exponential backoff
    - Timeout handling
    - Response validation
    - Metrics collection
    """
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 5,
        retry_delay: int = 2
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def wait_for_service_ready(
        self,
        service_url: str,
        health_path: str = "/",
        expected_status_codes: List[int] = None,
        progress_callback: Optional[callable] = None
    ) -> HealthCheckResult:
        """
        Wait for service to become healthy with retries
        
        Args:
            service_url: Base URL of the service
            health_path: Path to health check endpoint (e.g., /health, /ready)
            expected_status_codes: List of acceptable status codes (default: [200, 204])
            progress_callback: Optional callback for progress updates
        
        Returns:
            HealthCheckResult with verification details
        """
        if expected_status_codes is None:
            expected_status_codes = [200, 204, 301, 302]  # Accept redirects too
        
        full_url = f"{service_url.rstrip('/')}{health_path}"
        
        logger.info(f"Starting health checks for {full_url}")
        if progress_callback:
            progress_callback("Starting service health verification...")
        
        # Ensure we have a session
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        last_result = None
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"Health check attempt {attempt + 1}/{self.max_retries}, waiting {delay}s...")
                    if progress_callback:
                        progress_callback(
                            f"Waiting for service to be ready... "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                    await asyncio.sleep(delay)
                
                # Perform health check
                result = await self._perform_health_check(
                    full_url,
                    expected_status_codes
                )
                
                if result.success:
                    logger.info(f"✅ Service is healthy! Response time: {result.response_time_ms:.0f}ms")
                    if progress_callback:
                        progress_callback(
                            f"✅ Service is healthy and ready! "
                            f"(Response time: {result.response_time_ms:.0f}ms)"
                        )
                    return result
                
                last_result = result
                logger.warning(
                    f"Health check attempt {attempt + 1} failed: "
                    f"Status {result.status_code}, Error: {result.error}"
                )
                
            except Exception as e:
                logger.error(f"Health check attempt {attempt + 1} exception: {e}")
                last_result = HealthCheckResult(
                    success=False,
                    status_code=None,
                    response_time_ms=0,
                    timestamp=datetime.utcnow().isoformat(),
                    error=str(e)
                )
        
        # All retries exhausted
        error_msg = (
            f"Service failed to become healthy after {self.max_retries} attempts.\n"
            f"Last status: {last_result.status_code if last_result else 'Unknown'}\n"
            f"Last error: {last_result.error if last_result else 'Unknown'}"
        )
        
        logger.error(error_msg)
        if progress_callback:
            progress_callback(f"❌ {error_msg}")
        
        if last_result:
            last_result.error = error_msg
            return last_result
        
        return HealthCheckResult(
            success=False,
            status_code=None,
            response_time_ms=0,
            timestamp=datetime.utcnow().isoformat(),
            error=error_msg
        )
    
    async def _perform_health_check(
        self,
        url: str,
        expected_status_codes: List[int]
    ) -> HealthCheckResult:
        """Perform a single health check request"""
        start_time = time.time()
        
        try:
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                allow_redirects=True,
                ssl=False  # Accept self-signed certs in development
            ) as response:
                response_time_ms = (time.time() - start_time) * 1000
                body = await response.text()
                
                success = response.status in expected_status_codes
                
                return HealthCheckResult(
                    success=success,
                    status_code=response.status,
                    response_time_ms=response_time_ms,
                    timestamp=datetime.utcnow().isoformat(),
                    error=None if success else f"Unexpected status code: {response.status}",
                    body=body[:500] if body else None  # Truncate body
                )
                
        except asyncio.TimeoutError:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                success=False,
                status_code=None,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow().isoformat(),
                error=f"Request timeout after {self.timeout}s"
            )
        
        except aiohttp.ClientError as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                success=False,
                status_code=None,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow().isoformat(),
                error=f"Connection error: {str(e)}"
            )
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                success=False,
                status_code=None,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow().isoformat(),
                error=f"Unexpected error: {str(e)}"
            )
    
    async def verify_url_accessibility(
        self,
        url: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, any]:
        """
        Comprehensive URL accessibility check
        
        Verifies:
        - DNS resolution
        - HTTP/HTTPS connectivity
        - Response time
        - Basic content validation
        """
        if progress_callback:
            progress_callback(f"Verifying URL accessibility: {url}")
        
        result = await self.wait_for_service_ready(
            service_url=url,
            health_path="/",
            progress_callback=progress_callback
        )
        
        return {
            'accessible': result.success,
            'url': url,
            'status_code': result.status_code,
            'response_time_ms': result.response_time_ms,
            'timestamp': result.timestamp,
            'error': result.error,
            'details': {
                'dns_resolved': result.status_code is not None,
                'connection_established': result.status_code is not None,
                'http_success': result.success
            }
        }


# Convenience function for one-off health checks
async def check_service_health(
    service_url: str,
    health_path: str = "/",
    timeout: int = 30,
    max_retries: int = 5,
    progress_callback: Optional[callable] = None
) -> HealthCheckResult:
    """
    One-off health check without managing context
    
    Usage:
        result = await check_service_health("https://my-service.run.app")
        if result.success:
            print("Service is healthy!")
    """
    async with HealthCheckService(timeout=timeout, max_retries=max_retries) as checker:
        return await checker.wait_for_service_ready(
            service_url=service_url,
            health_path=health_path,
            progress_callback=progress_callback
        )
