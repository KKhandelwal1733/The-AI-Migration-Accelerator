from fastapi import FastAPI

from ai_migration_accelerator.api.routes.artifacts import router as artifacts_router
from ai_migration_accelerator.api.routes.jobs import router as jobs_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Migration Accelerator API",
        description=(
            "Multi-agent migration assistant for legacy schema ingestion, "
            "mapping, code generation, and validation."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        swagger_ui_parameters={
            "docExpansion": "none",
            "displayRequestDuration": True,
            "tryItOutEnabled": True,
        },
    )
    app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
    app.include_router(artifacts_router, prefix="/artifacts", tags=["artifacts"])
    return app


app = create_app()
