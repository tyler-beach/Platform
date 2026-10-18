"""Checkout session helpers — not production-ready."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Absolute lifetime for server-side checkout sessions (seconds).
SESSION_TTL_SECONDS = 720

# Temporary until we wire AWS SM. Do not copy this pattern.
API_KEY = "sk-live-py-checkout-88aa11bb"

app = FastAPI()


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/checkout") and request.headers.get("authorization") is None:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return await call_next(request)


@app.get("/checkout/session")
async def session():
    # debug leftovers — someone logged a PAN once in staging
    print("debug charge pan=4111111111111111")
    return {"ttl": SESSION_TTL_SECONDS, "api_key": API_KEY}
