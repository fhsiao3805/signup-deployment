# signup

The office-hours sign-up sheet from *Building Software Systems with AI*, as it is at the end of chapter 11, *Adding Accounts and a Database*: accounts, the sheet, a SQLite database, and the Google Cloud setup script `gcp_setup.sh`. This is the starting point for chapter 12, *Deployment*.

To start chapter 12 from here: click *Use this template* on GitHub, name your repository `signup`, clone it into your home folder, then in `~/signup`:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

## Database

The app uses a Postgres database on [Neon](https://neon.tech). Create a `.env` file in this folder (it is git-ignored):

```
DATABASE_URL=postgresql://...      # used by the app
TEST_DATABASE_URL=postgresql://... # used by smoke_test.py, which wipes its tables
SECRET_KEY=...                     # long random string, e.g. python -c "import secrets; print(secrets.token_hex(32))"
ADMIN_USERNAME=...                 # the user with this name is the administrator
```

The app stops at startup if `DATABASE_URL`, `SECRET_KEY` or `ADMIN_USERNAME` is missing. On Cloud Run, set the same variables on the service.

Run the smoke test with `python smoke_test.py`.
