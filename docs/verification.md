# Verification record

Verified on October 6, 2026, using Python 3.12 on Windows and a fresh isolated
dependency environment outside the repository.

## Automated checks

- **79 pytest cases passed.** Isolated in-memory databases; no model downloads in
  the suite. Covers accounts, password hashing, protection, CSRF, history privacy,
  admin safeguards, validation, errors, seeding, fallback, and chunk reduction.
- **Ruff checks and formatting passed.** Sources also parse with Python 3.10 syntax.
- **Dependency consistency passed:** `pip check` reported no broken requirements.
- **Seeding passed twice:** seven demonstration users and 21 summaries; a repeat
  invocation added zero users and zero summaries.
- **Git ignore checks passed:** environment files, runtime database/secret,
  bytecode, caches, virtual environments, and model binaries are excluded.
- All README screenshot references resolve to existing, real screenshots.

## Browser verification

Playwright drove the actual Flask server in Chromium. Checks passed for public
navigation, empty-input feedback, live counts, generation, clipboard copying,
text downloads, registration, demo/admin sign-in and sign-out, private history
details, forbidden admin access for normal members, user/summary filtering,
confirmed account deletion, dark-mode persistence, and narrow-screen layouts.

Twelve real screenshots are included in `docs/screenshots/`: the eleven standard
views and an additional live DistilBART result. Desktop captures use a 1440×900
viewport, with full-page captures for longer views; the mobile view uses 390×844.

## Real-model verification

Transformers 4.57.6 and PyTorch 2.14.1 loaded the actual
`sshleifer/distilbart-cnn-12-6` checkpoint from a cache outside the repository.
Real CPU inference passed for short, medium, and long summaries. A 1,090-word
document spanning two model input chunks also passed hierarchical summarization.
Token budgets were checked using the real tokenizer. A separate browser run
confirmed the live JSON endpoint returned a Transformer result.

The offline extractive engine was independently exercised through the browser
and test suite. Model-load and inference failures are tested with mocks. Model
weights and temporary verification environments are not part of the repository.

## Practical limits

CPU inference takes substantially longer than the extractive engine and depends
on document size and available hardware. Summaries require review against their
source. The app remains a single-host Flask/SQLite project; follow the
[deployment guide](deployment.md) before exposing it publicly. CI is configured
for Python 3.10 and 3.12, while the local full-stack run was verified on 3.12.

