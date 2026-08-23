import hmac
import logging
import os
from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, StringConstraints

logger = logging.getLogger(__name__)

# ---------- ENV CONFIG (Railway variables) ----------
FIX_QUOTE_HOST = os.environ.get("FIX_QUOTE_HOST", "")
FIX_TRADE_HOST = os.environ.get("FIX_TRADE_HOST", "")
FIX_SENDER_COMP_ID = os.environ.get("FIX_SENDER_COMP_ID", "")
FIX_ACCOUNT = os.environ.get("FIX_ACCOUNT", "")
FIX_PASSWORD = os.environ.get("FIX_PASSWORD", "")

# Comma separated list of host:port pairs a caller is allowed to point the
# bridge at. Empty means callers cannot override the configured hosts.
FIX_ALLOWED_HOSTS = {
    h.strip() for h in os.environ.get("FIX_ALLOWED_HOSTS", "").split(",") if h.strip()
}

API_KEY = os.environ.get("API_KEY", "")
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]
ENABLE_DOCS = os.environ.get("ENABLE_DOCS", "").lower() in {"1", "true", "yes"}

if not API_KEY:
    raise RuntimeError("API_KEY environment variable must be set")

app = FastAPI(
    title="IC Markets FIX Bridge",
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)

if CORS_ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )


def require_api_key(x_api_key: Annotated[str, Header()] = "") -> None:
    if not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )


def resolve_host(requested: Optional[str], configured: str) -> str:
    if requested is None or requested == configured:
        if not configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="FIX host is not configured",
            )
        return configured
    if requested not in FIX_ALLOWED_HOSTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Host is not allowed"
        )
    return requested


Symbol = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9._/-]{1,20}$")]
Name = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9._-]{1,50}$")]


# ---------- REQUEST MODELS ----------
class ConnectRequest(BaseModel):
    quote_host: Optional[str] = Field(default=None, max_length=255)
    trade_host: Optional[str] = Field(default=None, max_length=255)


class MarketDataRequest(BaseModel):
    symbols: List[Symbol] = Field(min_length=1, max_length=100)
    features: Optional[List[Name]] = Field(default=None, max_length=50)


class TechnicalAnalysisRequest(BaseModel):
    strategies: List[Name] = Field(min_length=1, max_length=50)
    features: Optional[List[Name]] = Field(default=None, max_length=50)


# ---------- ROOT ----------
@app.get("/")
def root():
    return {"status": "OK", "message": "IC Markets FIX Bridge running"}


# ---------- FIX CONNECT ----------
@app.post("/api/fix/connect", dependencies=[Depends(require_api_key)])
def connect_fix(req: ConnectRequest):
    quote_host = resolve_host(req.quote_host, FIX_QUOTE_HOST)
    trade_host = resolve_host(req.trade_host, FIX_TRADE_HOST)

    if not (FIX_SENDER_COMP_ID and FIX_ACCOUNT and FIX_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FIX session credentials are not configured",
        )

    # TODO: replace with real FIX session init (QuickFIX, etc.)
    logger.info("FIX connect requested (quote=%s, trade=%s)", quote_host, trade_host)

    return {"status": "CONNECTED", "quote_host": quote_host, "trade_host": trade_host}


# ---------- MARKET DATA ----------
@app.post("/api/fix/market_data", dependencies=[Depends(require_api_key)])
def market_data(req: MarketDataRequest):
    # TODO: subscribe/send FIX MarketDataRequest messages
    return {
        "status": "OK",
        "symbols": req.symbols,
        "features": req.features,
        "note": "FIX market data subscription placeholder",
    }


# ---------- TECHNICAL ANALYSIS ----------
@app.post("/api/fix/technical_analysis", dependencies=[Depends(require_api_key)])
def technical_analysis(req: TechnicalAnalysisRequest):
    # TODO: apply your strategies on incoming data streams
    signals = [{"strategy": s, "signal": "NEUTRAL"} for s in req.strategies]

    return {
        "status": "OK",
        "strategies": req.strategies,
        "signals": signals,
        "note": "Technical analysis placeholder",
    }
