import os
import sys
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Point the app at the test database, never the real one. This must happen
# before app is imported, because app reads DATABASE_URL (and creates the
# tables) on import. load_dotenv does not override variables set here.
load_dotenv(ROOT / ".env")
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()
if not TEST_DATABASE_URL:
    pytest.exit("TEST_DATABASE_URL is not set in .env.", returncode=2)
if TEST_DATABASE_URL == os.environ.get("DATABASE_URL", "").strip():
    pytest.exit("TEST_DATABASE_URL must differ from DATABASE_URL: tests empty its tables.", returncode=2)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
# Fixed values, so the tests don't depend on what is in .env.
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ADMIN_USERNAME"] = "admin"

import app as appmod  # noqa: E402

PASSWORD = "correct-horse"


@pytest.fixture(autouse=True)
def empty_tables():
    """Empty the test database's tables before each test."""
    with psycopg.connect(TEST_DATABASE_URL) as db:
        db.execute("TRUNCATE bookings, users RESTART IDENTITY CASCADE")
    yield


@pytest.fixture
def db():
    """A connection to the test database, for checking what the app stored."""
    with psycopg.connect(TEST_DATABASE_URL) as conn:
        yield conn


@pytest.fixture
def make_client():
    """Return a function that registers and logs in a user, giving their own client."""
    appmod.app.config["TESTING"] = True

    def _make(username, password=PASSWORD):
        client = appmod.app.test_client()
        client.post("/register", data={"username": username, "password": password})
        r = client.post("/login", data={"username": username, "password": password})
        assert r.status_code == 302, f"could not log in as {username}"
        return client

    return _make


@pytest.fixture
def anon_client():
    appmod.app.config["TESTING"] = True
    return appmod.app.test_client()
