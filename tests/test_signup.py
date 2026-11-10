from urllib.parse import urlparse

SLOT = {"weekday": "1", "start": "14:30"}  # Tuesday 2:30 pm


def booking_owner(db, weekday=1, start="14:30"):
    """Username of whoever holds the slot, or None if it is free."""
    row = db.execute(
        "SELECT u.username FROM bookings b JOIN users u ON u.id = b.user_id "
        "WHERE b.weekday = %s AND b.start = %s",
        (weekday, start),
    ).fetchone()
    return row[0] if row else None


def test_visitor_not_logged_in_is_sent_to_login(anon_client):
    r = anon_client.get("/sheet")
    assert r.status_code == 302
    assert urlparse(r.headers["Location"]).path == "/login"


def test_password_shorter_than_8_characters_is_refused(anon_client, db):
    anon_client.post("/register", data={"username": "shorty", "password": "1234567"})
    row = db.execute("SELECT 1 FROM users WHERE username = 'shorty'").fetchone()
    assert row is None, "a 7-character password was accepted at registration"


def test_password_of_8_characters_is_accepted(anon_client, db):
    anon_client.post("/register", data={"username": "eight", "password": "12345678"})
    row = db.execute("SELECT 1 FROM users WHERE username = 'eight'").fetchone()
    assert row is not None


def test_logged_in_user_can_book_free_slot(make_client, db):
    bob = make_client("bob")
    r = bob.post("/book", data=SLOT, follow_redirects=True)
    assert r.status_code == 200
    assert booking_owner(db) == "bob"


def test_slot_booked_by_another_user_cannot_be_booked(make_client, db):
    bob = make_client("bob")
    carol = make_client("carol")
    bob.post("/book", data=SLOT)
    r = carol.post("/book", data=SLOT, follow_redirects=True)
    assert "already been taken" in r.get_data(as_text=True)
    assert booking_owner(db) == "bob"


def test_user_can_cancel_own_booking(make_client, db):
    bob = make_client("bob")
    bob.post("/book", data=SLOT)
    bob.post("/cancel", data=SLOT)
    assert booking_owner(db) is None


def test_user_cannot_cancel_another_users_booking(make_client, db):
    bob = make_client("bob")
    carol = make_client("carol")
    bob.post("/book", data=SLOT)
    carol.post("/cancel", data=SLOT)
    assert booking_owner(db) == "bob"


def test_admin_can_cancel_anyones_booking(make_client, db):
    bob = make_client("bob")
    admin = make_client("admin")
    bob.post("/book", data=SLOT)
    admin.post("/cancel", data=SLOT)
    assert booking_owner(db) is None, "the administrator could not cancel another user's booking"
