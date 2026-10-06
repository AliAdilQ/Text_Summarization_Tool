# Application screenshots

These images show the actual seeded Flask application running locally. They were
captured with Playwright at a desktop viewport of 1440×900 (full-page captures
where appropriate), plus a 390×844 mobile viewport. No UI mockups are presented
as application screenshots. All visible accounts and content are local demo data.

| File | View |
| --- | --- |
| [home.png](home.png) | Full landing page |
| [summarizer.png](summarizer.png) | Empty summarization workspace |
| [summary-result.png](summary-result.png) | Actual extractive-engine summary and metrics |
| [transformer-result.png](transformer-result.png) | Actual DistilBART summary through the live web interface |
| [login.png](login.png) | Sign-in page |
| [user-dashboard.png](user-dashboard.png) | Signed-in demo user workspace |
| [user-history.png](user-history.png) | Demo user's private reading library |
| [admin-dashboard.png](admin-dashboard.png) | Live database analytics |
| [admin-users.png](admin-users.png) | User management |
| [admin-summaries.png](admin-summaries.png) | Summary management |
| [dark-mode.png](dark-mode.png) | Admin workspace in dark mode |
| [mobile-summarizer.png](mobile-summarizer.png) | Responsive mobile workspace |

To reproduce them, install optional development dependencies and Chromium,
seed the database, and run the app:

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
python seed.py
python run.py
```

In another terminal using the same virtual environment:

```bash
python scripts/capture_screenshots.py
```

The script also checks registration, sign-in/out, generation, copy/download,
admin access restrictions, filters, confirmed account deletion, theme persistence,
internal navigation, and mobile overflow. Run it on a local seeded demo instance.

The additional Transformer result was captured from the same live workspace
after caching DistilBART with `flask --app run download-model` and restarting the
server. The standard script uses whichever engine is available; it does not
download model weights. To reproduce an abstractive result, predownload the model
and generate the built-in example with the default `auto` backend.
