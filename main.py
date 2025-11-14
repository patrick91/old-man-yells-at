"""FastAPI meme generator application."""

from fastapi import FastAPI

from app.routes.meme import router as meme_router

app = FastAPI(title="Meme Generator API")

# Include routers
app.include_router(meme_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
