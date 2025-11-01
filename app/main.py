from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .routers.search import router as search_router
from .routers.scraping import router as scraping_router
from .routers.pdf import router as pdf_router
from .routers.llm import router as llm_router
from .routers.crm import router as crm_router
from datetime import datetime
import uvicorn
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db, test_connection

app = FastAPI(
    title="LLM-based CRM Pipeline API",
    description="API for LLM-based CRM pipeline: generate personas, outreach sequences, and more from company data",
    version="1.0.0"
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
app.include_router(crm_router, prefix="/api/v1", tags=["CRM Service"])


@app.on_event("startup")
async def startup_event():
    """Test database connection on startup"""
    print("Starting application...")
    test_connection()


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


@app.get("/db-ping")
def ping_db(db: Session = Depends(get_db)):
    """
    Simple ping test
    """
    try:
        result = db.execute(text("SELECT 1 as ping"))
        return {
            "status": "success",
            "ping": result.scalar()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
