from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .routers.search import router as search_router
from .routers.scraping import router as scraping_router
from .routers.pdf import router as pdf_router
from .routers.llm import router as llm_router
from .routers.pipeline_evaluate import router as pipeline_evaluate_router
from .routers.crm import router as crm_router
from .routers.export import router as export_router
from datetime import datetime
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan event handler"""
    # Startup
    print("Starting application...")
    yield
    # Shutdown (if needed in the future)
    pass


app = FastAPI(
    title="LLM-based CRM Pipeline API",
    description="API for LLM-based CRM pipeline: generate personas, outreach sequences, and more from company data",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(search_router, prefix="/api/v1", tags=["Search"])
app.include_router(scraping_router, prefix="/api/v1", tags=["Data Scraping"])
app.include_router(pdf_router, prefix="/api/v1", tags=["PDF Processing"])
app.include_router(llm_router, prefix="/api/v1", tags=["LLM Service"])
app.include_router(pipeline_evaluate_router, prefix="/api/v1", tags=["Pipeline Evaluate"])
app.include_router(crm_router, prefix="/api/v1", tags=["CRM Service"])
app.include_router(export_router, prefix="/api/v1", tags=["Export"])


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
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
