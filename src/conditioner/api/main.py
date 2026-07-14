from fastapi import FastAPI

from conditioner.api.auth import router as auth_router

app = FastAPI(title="Conditioner")
app.include_router(auth_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
