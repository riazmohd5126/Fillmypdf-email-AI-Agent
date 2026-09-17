"""One-off helper to create tables from the current models.

For production, replace with proper migrations (e.g. Alembic) once the
schema stabilizes — see design doc build plan item 1.
"""

from src.db.base import init_db

if __name__ == "__main__":
    init_db()
    print("Tables created.")
