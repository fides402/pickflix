from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import jobs, models, plugins

app = FastAPI(title="Audio Reference Matcher")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models.router)
app.include_router(plugins.router)
app.include_router(jobs.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
