import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure project root is on sys.path for imports like `from app.main import app`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


# Ensure required environment variables exist for imports that rely on settings
os.environ.setdefault("SMART_PROXY_API_KEY", "test_api_key")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


