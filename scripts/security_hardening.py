# scripts/security_hardening.py

from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.cors import CORSMiddleware

def apply_owasp_hardening(app: FastAPI):
    # A02: Secure Headers
    @app.middleware("http")
    async def secure_headers(request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=()"
        return response

    # A01: Prevent Host Header attacks
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )

    # A05: Secure CORS (for stricter policy for prod)
    # Already handled in `cors.py`
    # app.add_middleware(CORSMiddleware, ...)

    # A06: Enforce HTTPS (only on deployed version behind HTTPS proxy)
    # app.add_middleware(HTTPSRedirectMiddleware)
