from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import adaptron


def create_app() -> FastAPI:
    app = FastAPI(
        title="Adaptron API",
        description="End-to-end LLM Fine-tuning Framework",
        version=adaptron.__version__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    from adaptron.api.routes.wizard import router as wizard_router
    from adaptron.api.routes.pipelines import router as pipelines_router

    app.include_router(wizard_router)
    app.include_router(pipelines_router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": adaptron.__version__}

    return app
