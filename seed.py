"""Create the schema and idempotently populate local demonstration data."""

from app import create_app
from app.services.seed import seed_database

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        print(seed_database())
