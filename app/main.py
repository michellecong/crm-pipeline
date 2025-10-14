# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.search import router
from datetime import datetime
import uvicorn

app = FastAPI(
    title="LLM-based CRM Pipeline API",
    description="API forLLM-based CRM pipeline: generate personas, outreach sequences, and more from company data",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1", tags=["Search"])

@app.get("/")
def root():
    return {
        "message": "LLM-based CRM Pipeline API",
        "docs": "/docs",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)