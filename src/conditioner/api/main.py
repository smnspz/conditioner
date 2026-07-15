from fastapi import FastAPI

from conditioner.api.routes.auth import router as auth_router
from conditioner.api.routes.constraints import router as constraints_router
from conditioner.api.routes.questionnaire import router as questionnaire_router
from conditioner.api.routes.readiness import router as readiness_router
from conditioner.api.routes.workouts import router as workouts_router

app = FastAPI(title="Conditioner")
app.include_router(auth_router)
app.include_router(constraints_router)
app.include_router(questionnaire_router)
app.include_router(readiness_router)
app.include_router(workouts_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return a simple liveness response."""

    # Return health status
    return {"status": "ok"}
