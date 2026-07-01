# Jobs Academy Backend — Final Package

This package was verified via a genuine fresh-clone test: new git clone, new virtualenv, new database, following the steps below exactly. `manage.py check` is clean, all migrations apply with zero errors, and a real signup request against a brand-new empty database succeeds end to end.

## What's different from earlier deliverables this session

Two earlier "complete" packages had fixes that existed only in an ad-hoc working directory and were never actually committed to this project's git history. This package starts from a fresh `git clone` of the real, committed history (`git log` works, you can see every change), with the previously-missing pieces added properly:

- App no longer crashes on boot without `credentials.json` (Firebase) or `config/serviceAccountKey.json` (FCM) — both are optional now; push notifications are simply disabled until you supply them.
- `django-celery-beat` added to `requirements.txt` (it was referenced in `INSTALLED_APPS` but never listed as a dependency).
- Migrations added for `govt_jobs`, `quickquiz`, `written_exam`, `news`, `notifications`, `language_center` — these apps previously had **no migrations in the repository at all**, meaning their database tables would never have been created on a fresh install.
- A substantial `quiz` migration covering models that existed in code but were never migrated (`PastExam`, `PastExamAttempt`, `ExamQuestion`, `Department`, `Organization`, `Position`, `ExamType`, and others), plus the `ExamAttempt.score` field fix from the exam-submission crash bug.
- A small, safe `users` migration (field alterations only, no data risk).

## One thing deliberately NOT included — read this before going further

There's an additional `subscription` migration that is **not** in this package. It deletes seven existing database models (`Coupon`, `Payment`, `Refund`, `SubscriptionPackage`, and others) to replace them with newer ones the code has already moved to. I have no way to know whether your actual database has real payment/subscription data in those tables, so I'm not bundling it here. If you need it, ask — I'll provide it separately with the same care, after you've confirmed (or backed up) what's actually in those tables.

Until that migration is applied, the newer subscription models (`SubscriptionPlanTier`, `SubscriptionPlanPrice`, `PlanExamAccessLimit`, `UserExamAccess` — documented in `API_REFERENCE.md` §11) won't have database tables, so those specific endpoints will error. Everything else in the API reference works.

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # or `. venv/bin/activate` depending on your shell
pip install -r requirements.txt
```

### Database

```bash
sudo -u postgres psql -c "CREATE USER quiz_user WITH PASSWORD 'Bridgers@123';"
sudo -u postgres psql -c "CREATE DATABASE quiz_portal OWNER quiz_user;"
```

These exact values are hardcoded in `quiz_portal/settings.py`. If you want different credentials, edit that file directly (the `DATABASE_URL` env-var path exists in code but isn't actually wired up — it's commented out).

If your Postgres isn't on port `5433`, either reconfigure it to use that port, or edit the `PORT` value in `quiz_portal/settings.py`.

### Environment variables

Copy `.env.example` to `.env` and fill in real values:
```bash
cp .env.example .env
```

The app boots fine with placeholder values for the email/OAuth vars — you'll just lose OTP emails and Google social login until they're real.

**Important:** `SECRET_KEY` and the database credentials have defaults baked into `quiz_portal/settings.py` that are visible in this repo's git history. Don't rely on those defaults for anything beyond local throwaway testing — set real values via `.env` for any deployment that matters. `.env.example` has a one-liner for generating a fresh `SECRET_KEY`.

### Credentials (optional)

If you want push notifications working:
- `credentials.json` (Firebase Admin SDK) → project root
- `config/serviceAccountKey.json` (FCM) → `config/` folder

Without them, the app runs fine; those specific features just won't work.

### Migrate and run

```bash
python3 manage.py migrate
python3 manage.py createsuperuser --phone_number 01700000000
python3 manage.py runserver 0.0.0.0:8001
```

Or via Daphne (matches how this runs in production):
```bash
daphne -b 0.0.0.0 -p 8001 quiz_portal.asgi:application
```

### Verify

```bash
curl http://127.0.0.1:8001/
curl http://127.0.0.1:8001/api/schema/swagger-ui/
```

## Project size note

This package is ~176MB, mostly `frontend/static` and `static/` — the legacy Django-template UI's images, CSS, and JS, kept in case you need the old site running alongside the new Angular frontend during the transition. Safe to delete once you no longer need it; `staticfiles/` in particular is just a `collectstatic` build artifact and is fully regenerable.

## CORS

`django-cors-headers` is enabled with `CORS_ALLOW_ALL_ORIGINS = True`. Tighten this once your frontend's domain is fixed:
```python
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = ['http://localhost:4200']
```

## Full endpoint reference

See `API_REFERENCE.md` from the earlier deliverable for request/response shapes across every endpoint. Note its §11 (subscriptions) describes the newer models that need the migration mentioned above.
