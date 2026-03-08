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
    from adaptron.api.routes.playground import router as playground_router

    app.include_router(wizard_router)
    app.include_router(pipelines_router)
    app.include_router(playground_router)

    from adaptron.api.routes.connectors import router as connectors_router
    app.include_router(connectors_router)

    from adaptron.api.routes.schedules import router as schedules_router
    app.include_router(schedules_router)

    from adaptron.api.routes.research import router as research_router
    app.include_router(research_router)

    from adaptron.api.routes.validate import router as validate_router
    app.include_router(validate_router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": adaptron.__version__}

    return app
