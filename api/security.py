"""HTTP security controls for SmartHub API routes."""
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
        self.limits = {
            "/api/auth/login": 12,
            "/api/auth/register": 8,
            "/api/auth/google": 12,
            "/api/detector/text": 5,
            "/api/media": 6,
            "/api/chat": 20,
            "/api/images/generate": 3,
            "/api/images/edit": 3,
            "/api/video/generate": 2,
        }

    def secure(self, response, request):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin" if request.method == "GET" and request.url.path.startswith("/api/media/") else "same-site"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path.startswith("/api/"):
            length = request.headers.get("content-length")
            if length:
                try:
                    if int(length) > self.max_body_bytes:
                        return self.secure(JSONResponse({"detail": "حجم الطلب أكبر من الحد المسموح."}, status_code=413), request)
                except ValueError:
                    return self.secure(JSONResponse({"detail": "ترويسة حجم الطلب غير صالحة."}, status_code=400), request)
            limit = self.limits.get(path)
            if limit:
                client = request.client.host if request.client else "unknown"
                key = (client, path)
                now = time.monotonic()
                bucket = self.events[key]
                while bucket and now - bucket[0] > self.window_seconds:
                    bucket.popleft()
                if len(bucket) >= limit:
                    return self.secure(JSONResponse({"detail": "طلبات كثيرة. انتظر قليلاً ثم أعد المحاولة."}, status_code=429), request)
                bucket.append(now)
        response = await call_next(request)
        return self.secure(response, request)


def install_security(app):
    app.add_middleware(RequestSecurityMiddleware)
