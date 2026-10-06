# Deployment guide

The application has a production-style architecture and local demonstration
workflow. A public deployment also needs infrastructure and operational setup.

## Configure the service

1. Install Python 3.10+ and dependencies from `requirements.txt` in an isolated
   environment. Use a CPU-compatible PyTorch build or configure the appropriate
   accelerator packages for your host.
2. Generate an independent secret: `python -c "import secrets; print(secrets.token_hex(32))"`.
3. Supply `FLASK_ENV=production`, `SECRET_KEY`, and `SESSION_COOKIE_SECURE=true`
   through environment variables or a protected `.env` file.
4. Give only the service account access to `instance/` and any model cache.
   Tables are created automatically. Do **not** run the demo seed command.
5. Download the model before accepting traffic with
   `flask --app run download-model`. This downloads public model weights to the
   Hugging Face cache. Leave `MODEL_ALLOW_DOWNLOAD=false` while serving requests.
6. Run `waitress-serve --host=127.0.0.1 --port=8000 --call app:create_app` and put
   an HTTPS reverse proxy in front of it. Waitress works on Windows and Linux.

When deploying an existing demo instance, delete demonstration accounts and
content before changing `FLASK_ENV`; create a new independent admin account.
To create an administrator on a clean database, open `flask --app run shell`:

```python
from getpass import getpass
from app.extensions import db
from app.models import User

admin = User(username="workspace_admin", email="your-admin@example.com", is_admin=True)
admin.set_password(getpass("New administrator password: "))
db.session.add(admin)
db.session.commit()
```

Use your real administrative email and a unique password. The password is read
without echoing it to the terminal and is stored as a Werkzeug password hash.

## Capacity and operations

- DistilBART has roughly 306 million parameters. Plan for several GB of available
  RAM per worker and profile CPU latency with representative documents.
- The model is loaded once per process. Inference is serialized within a worker
  to avoid simultaneous high-memory jobs. CPU-heavy requests can take minutes;
  configure proxy timeouts accordingly. For higher traffic, introduce a task
  queue and explicit per-user quotas.
- SQLite is appropriate for a small, single-host application. Keep the database
  on local disk, back it up consistently, and move to PostgreSQL plus schema
  migrations when concurrency or operational needs grow.
- `db.create_all()` creates missing tables; it does not migrate existing schemas.
  Use Alembic/Flask-Migrate before shipping schema changes to a populated database.
- Add reverse-proxy rate limits for login, registration, and summarization. The
  app does not currently implement distributed throttling, email verification,
  password reset, or multifactor authentication.
- Do not enable the Flask debugger for public traffic. Errors are logged on the
  server; users receive styled error pages or JSON error messages.
- Summaries can be inaccurate. Define retention rules and communicate that
  authorized admins can inspect saved text. Guest inputs are not persisted by
  application code; web server logging and host policies need separate review.

## Health and shutdown

`GET /health` returns `{"status":"ok"}` for a running app. It is a liveness check,
not a model readiness or database integrity check. Stop the server normally so
in-flight requests can finish. Monitor application logs and failed requests.

