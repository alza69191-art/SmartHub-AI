"""Baseline HTTP security controls for SmartHub API."""
import time
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RequestSecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_bytes=15 * 1024 * 1024):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes
        self.events = defaultdict(deque)
        self.window_seconds = 60
        self.max_auth_requests = 12

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path.startswith("/api/"):
            length = request.headers.get("content-length")
            if length:
                try:
                    if int(length) > self.max_body_bytes:
                        return JSONResponse({"detail": "حجم الطلب أكبر من الحد المسموح."}, status_code=413)
                except ValueError:
                    return JSONResponse({"detail": "ترويسة حجم الطلب غير صالحة."}, status_code=400)
            if path in ("/api/auth/login", "/api/auth/register", "/api/auth/google"):
                client = request.client.host if request.client else "unknown"
                key = (client, path)
                now = time.monotonic()
                bucket = self.events[key]
                while bucket and now - bucket[0] > self.window_seconds:
                    bucket.popleft()
                if len(bucket) >= self.max_auth_requests:
                    return JSONResponse({"detail": "طلبات كثيرة. انتظر دقيقة ثم أعد المحاولة."}, status_code=429)
                bucket.append(now)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

def install_security(app):
    app.add_middleware(RequestSecurityMiddleware)
