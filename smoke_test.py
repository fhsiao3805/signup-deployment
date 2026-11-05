import os
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)
sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv

# Run against the test database, never the real one. Set DATABASE_URL before
# importing app, since app reads it (and creates the tables) on import.
load_dotenv()
TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]
if TEST_DATABASE_URL == os.environ.get("DATABASE_URL"):
    sys.exit("TEST_DATABASE_URL must differ from DATABASE_URL: the smoke test wipes its tables.")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
# Fixed test values, so the test doesn't depend on what is in .env.
os.environ["SECRET_KEY"] = "smoke-test-secret"
os.environ["ADMIN_USERNAME"] = "alice"

import psycopg

# Start from empty tables so every run sees the same state.
with psycopg.connect(TEST_DATABASE_URL) as db:
    db.execute("DROP TABLE IF EXISTS bookings, users")

import app as appmod

appmod.app.config["TESTING"] = True
c = appmod.app.test_client()

def body(r):
    return r.get_data(as_text=True)

r = c.get("/")
assert r.status_code == 200 and "not logged in" in body(r), body(r)

# Not on Cloud Run, so the session cookie must not be marked Secure.
assert appmod.app.config["SESSION_COOKIE_SECURE"] is False

# Registered first, but not named by ADMIN_USERNAME, so not the administrator.
c.post("/register", data={"username": "early", "password": "pw"})

r = c.post("/register", data={"username": "alice", "password": "pw"}, follow_redirects=True)
assert "Account created" in body(r), body(r)

r = c.post("/register", data={"username": "alice", "password": "pw"})
assert "already taken" in body(r), body(r)

r = c.post("/register", data={"username": "", "password": "pw"})
assert "Username is required" in body(r), body(r)

r = c.post("/login", data={"username": "alice", "password": "wrong"})
assert "Incorrect" in body(r), body(r)

r = c.post("/login", data={"username": "alice", "password": "pw"}, follow_redirects=True)
assert "logged in as <strong>alice</strong>" in body(r), body(r)

r = c.post("/logout", follow_redirects=True)
assert "logged out" in body(r) and "not logged in" in body(r), body(r)

r = c.post("/logout", follow_redirects=True)
assert "Please log in first" in body(r), body(r)

# Password must be hashed, not stored in plain text.
with psycopg.connect(TEST_DATABASE_URL) as db:
    row = db.execute("SELECT password_hash FROM users").fetchone()
assert row[0] != "pw" and row[0].startswith(("scrypt:", "pbkdf2:")), row

# --- Sign-up sheet ---------------------------------------------------------

def login(username):
    c.post("/logout")
    r = c.post("/login", data={"username": username, "password": "pw"}, follow_redirects=True)
    assert f"Welcome, {username}" in body(r), body(r)

# The sheet needs a login.
r = c.get("/sheet", follow_redirects=True)
assert "Please log in first" in body(r), body(r)

c.post("/register", data={"username": "bob", "password": "pw"})

# early registered first but is not the administrator.
login("early")
r = c.get("/sheet")
assert "You are the administrator" not in body(r), body(r)

# alice is named by ADMIN_USERNAME, so she is the administrator.
login("alice")
r = c.get("/sheet")
assert r.status_code == 200 and "You are the administrator" in body(r), body(r)
assert body(r).count("<th>") == 1 + 5 + 4, body(r)        # corner, 5 days, 4 time rows
assert body(r).count(">Book</button>") == 20, body(r)      # all 20 slots free
assert "2:00 pm" in body(r) and "4:00 pm" in body(r), body(r)

# bob is not the administrator; he books a slot.
login("bob")
r = c.get("/sheet")
assert "You are the administrator" not in body(r), body(r)
r = c.post("/book", data={"weekday": "2", "start": "14:30"}, follow_redirects=True)
assert "Booked Wednesday at 2:30 pm" in body(r), body(r)
assert "Yours" in body(r) and ">Cancel</button>" in body(r), body(r)
assert body(r).count(">Book</button>") == 19, body(r)

# Booking the same slot twice (or an invalid slot) fails.
r = c.post("/book", data={"weekday": "2", "start": "14:30"}, follow_redirects=True)
assert "already been taken" in body(r), body(r)
r = c.post("/book", data={"weekday": "5", "start": "14:30"}, follow_redirects=True)
assert "not a valid slot" in body(r), body(r)
r = c.post("/book", data={"weekday": "0", "start": "16:00"}, follow_redirects=True)
assert "not a valid slot" in body(r), body(r)

# A third user sees the slot as taken, without the name, and cannot book or cancel it.
c.post("/register", data={"username": "carol", "password": "pw"})
login("carol")
r = c.get("/sheet")
assert ">Taken</span>" in body(r) and "bob" not in body(r).split("<table")[1], body(r)
r = c.post("/book", data={"weekday": "2", "start": "14:30"}, follow_redirects=True)
assert "already been taken" in body(r), body(r)
r = c.post("/cancel", data={"weekday": "2", "start": "14:30"}, follow_redirects=True)
assert "no booking in that slot" in body(r) and ">Taken</span>" in body(r), body(r)

# The administrator sees who booked it.
login("alice")
r = c.get("/sheet")
assert "Taken by <strong>bob</strong>" in body(r), body(r)

# bob cancels his own booking and the slot is free again.
login("bob")
r = c.post("/cancel", data={"weekday": "2", "start": "14:30"}, follow_redirects=True)
assert "Cancelled Wednesday at 2:30 pm" in body(r), body(r)
assert body(r).count(">Book</button>") == 20, body(r)

print("ALL SMOKE TESTS PASSED")
