import asyncio
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from starlette.requests import Request
from starlette.responses import Response

from security import RequestSecurityMiddleware


def make_request(path="/api/example", method="GET", headers=None):
    return Request({
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 443),
    })


class SecurityMiddlewareTests(unittest.TestCase):
    def setUp(self):
        self.middleware = RequestSecurityMiddleware(lambda scope, receive, send: None)

    def test_api_responses_are_not_cached(self):
        request = make_request("/api/profile")
        response = self.middleware.secure(Response(), request)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")

    def test_public_media_can_be_embedded_cross_origin(self):
        request = make_request("/api/media/123", method="GET")
        response = self.middleware.secure(Response(), request)
        self.assertEqual(response.headers["Cross-Origin-Resource-Policy"], "cross-origin")
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_other_api_routes_remain_same_site(self):
        request = make_request("/api/profile")
        response = self.middleware.secure(Response(), request)
        self.assertEqual(response.headers["Cross-Origin-Resource-Policy"], "same-site")

    def test_rejects_oversized_content_length(self):
        request = make_request("/api/media", method="POST", headers={"content-length": str(16 * 1024 * 1024)})
        async def run():
            async def call_next(_request):
                return Response("unexpected")
            return await self.middleware.dispatch(request, call_next)
        response = asyncio.run(run())
        self.assertEqual(response.status_code, 413)

    def test_rate_limits_expensive_provider_requests(self):
        async def run():
            async def call_next(_request):
                return Response("ok")
            responses = []
            for _ in range(4):
                responses.append(await self.middleware.dispatch(
                    make_request("/api/images/generate", method="POST"), call_next
                ))
            return responses
        responses = asyncio.run(run())
        self.assertTrue(all(response.status_code == 200 for response in responses[:3]))
        self.assertEqual(responses[3].status_code, 429)

    def test_rate_limits_auth_requests(self):
        async def run():
            async def call_next(_request):
                return Response("ok")
            results = []
            for _ in range(13):
                results.append(await self.middleware.dispatch(
                    make_request("/api/auth/login", method="POST"), call_next
                ))
            return results
        responses = asyncio.run(run())
        self.assertTrue(all(response.status_code == 200 for response in responses[:12]))
        self.assertEqual(responses[12].status_code, 429)


if __name__ == "__main__":
    unittest.main()
