"""Rebuilt LinkGuard API; no scanned URL fetching or request-body logging."""

import asyncio, os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictStr
from starlette.concurrency import run_in_threadpool
from linkguard.features import FEATURE_SCHEMA_VERSION
from linkguard.urltools import normalize_url, URLValidationError
from linkguard.model import URLDetector, ModelUnavailableError


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        for key, value in scope.get("headers", []):
            if key.lower() == b"content-length":
                try:
                    length = int(value)
                    if length < 0:
                        raise ValueError()
                except ValueError:
                    return await JSONResponse(
                        {"detail": "요청 형식이 올바르지 않습니다."}, status_code=400
                    )(scope, receive, send)
                if length > 16384:
                    return await JSONResponse(
                        {"detail": "요청 본문이 너무 큽니다."}, status_code=413
                    )(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > 16384:
                return await JSONResponse({"detail": "요청 본문이 너무 큽니다."}, status_code=413)(
                    scope, receive, send
                )
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    url: StrictStr = Field(min_length=1, max_length=4096)


class Prediction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    url: str
    status: Literal["safe", "caution", "danger"]
    score: int = Field(ge=0, le=100)
    reasons: list[str] = Field(min_length=1, max_length=12)
    model_version: str = Field(min_length=1, max_length=120)


def create_app(model_path=None):
    path = (
        model_path
        if model_path is not None
        else os.getenv(
            "LINKGUARD_MODEL_PATH",
            str(Path(__file__).resolve().parent / "artifacts/linkguard.joblib"),
        )
    )

    @asynccontextmanager
    async def lifespan(app):
        app.state.gate = asyncio.Semaphore(4)
        try:
            app.state.detector = await run_in_threadpool(URLDetector.load, path)
        except ModelUnavailableError:
            app.state.detector = None
        yield
        app.state.detector = None

    app = FastAPI(title="LinkGuard Rebuilt", lifespan=lifespan)
    app.state.detector = None
    app.add_middleware(BodyLimit)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        return JSONResponse({"detail": "URL 입력 형식이 올바르지 않습니다."}, status_code=422)

    @app.get("/health")
    async def health():
        return {
            "status": "ready" if app.state.detector else "model_unavailable",
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
        }

    @app.post("/predict", response_model=Prediction)
    async def predict(request: Request):
        try:
            url = normalize_url(request.url)
        except (URLValidationError, ValueError):
            raise HTTPException(422, "URL 입력 형식이 올바르지 않습니다.") from None
        if app.state.detector is None:
            raise HTTPException(503, "학습된 분석 모델이 준비되지 않았습니다.")
        gate = app.state.gate
        if gate.locked():
            raise HTTPException(503, "분석 요청이 많습니다.")
        await gate.acquire()
        try:
            return await run_in_threadpool(app.state.detector.predict, url)
        except Exception:
            app.state.detector = None
            raise HTTPException(503, "분석 모델을 사용할 수 없습니다.") from None
        finally:
            gate.release()

    return app


app = create_app()
