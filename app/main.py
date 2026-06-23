"""FastAPI meme generator application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.landing import router as landing_router
from app.routes.meme import router as meme_router
from app.routes.slack import router as slack_router

app = FastAPI(title="Meme Generator API")
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Static landing page assets need to be registered before the catch-all meme route.
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(landing_router)
app.include_router(meme_router)
app.include_router(slack_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
