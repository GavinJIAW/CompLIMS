# CompLIMS baseline setup

This document records the long-term local setup and minimum validation baseline for development on the accepted P0 Foundation. It separates local configuration, disposable test resources, and the engineering tools that are not mandatory P0 gates.

## Local configuration and initialization

- Backend: copy `src/backend/conf/env.example.py` to `env.py` in the same directory. The copy is ignored. Set `DJANGO_SECRET_KEY`, the independent `JWT_SIGNING_KEY`, and database credentials through the supported local configuration or environment variables. Never commit credentials or the local file. Credentials previously exposed in source or local exports should be rotated before deployment.
- Frontend: copy `src/web/.env.example` to `.env`. Set non-secret Vite settings appropriate to each deployment. Local `.env.*` files are ignored. `VITE_*` values are public browser configuration, never credentials.
- Initialization inputs: local `init_users.json` and `init_systemconfig.json` under `src/backend/coreadmin/system/fixtures/` are excluded because they can contain password hashes or a default password. Sanitized `.example.json` counterparts are provided. Copy them to their corresponding local names only when deliberately preparing initialization. Example users have unusable passwords (`!`); configure passwords through an approved administration process. Copying configuration or fixtures does not authorize database initialization, password resets, or migration of an existing development database.
- Existing Django migrations, local FastCrud documentation, logos, and the design/review documents under `docs/` remain part of the foundation. Do not use development security settings unchanged for a public deployment; configure the required production secrets, hosts, origins, and private storage explicitly.

## Backend validation baseline

Use the existing backend environment:

```text
cd src/backend
conda activate dvadmin3_env
```

The verified version baseline is Python 3.11.x, Django 4.2.14, Django REST Framework 3.15.2, and PostgreSQL 16.x. Python and PostgreSQL patch versions are not permanent pins. Backend dependencies are exact-pinned in `requirements.txt`; validation of the existing environment does not imply that installation on every fresh platform has been tested.

The formal foundation test entry is:

```text
python -B manage.py test coreadmin.foundation_tests --settings=application.settings_test
```

### PostgreSQL test isolation

`application.settings_test` requires an independent PostgreSQL test database and all five environment variables, supplied securely without recording credentials in Git or logs:

- `COMPLIMS_TEST_DB_NAME`
- `COMPLIMS_TEST_DB_USER`
- `COMPLIMS_TEST_DB_PASSWORD`
- `COMPLIMS_TEST_DB_HOST`
- `COMPLIMS_TEST_DB_PORT`

Provision a disposable connection database whose name matches `complims_test_[a-z0-9_]{1,40}`. Django creates a separate `test_<NAME>` database for the test suite. Use a dedicated test role with the necessary database creation permissions and no access to development or production data. A safe database name is not a substitute for database privilege isolation.

Never use the development database `lims` as the foundation test target. Test settings isolate cache, file storage, and ManagedFile temporary storage, and disable business-data initialization on URL import.

### Clean-checkout backend validation

After provisioning the disposable PostgreSQL database and setting the variables above, run from `src/backend` in `dvadmin3_env`:

```text
python -B manage.py migrate --noinput --settings=application.settings_test
python -B manage.py test coreadmin.foundation_tests --settings=application.settings_test
python -B manage.py check --settings=application.settings_test
python -B manage.py makemigrations --check --dry-run --settings=application.settings_test
```

Stop on any nonzero exit code. The first command migrates only the dedicated disposable connection database; the test command uses Django's separate test database. Django normally destroys its test database on completion. Afterwards, destroy the dedicated disposable connection database and verify that no databases owned by this validation run remain. Never apply this cleanup to an existing development or production database.

Do not use unlabelled legacy test discovery or substitute development settings for `application.settings_test`.

## Frontend validation baseline

Use Node 20.19.5 and Yarn 1.22.22:

```text
cd src/web
nvm use 20.19.5
yarn --version
yarn install --frozen-lockfile
yarn run build
```

Verify that Yarn reports 1.22.22 and stop on any command failure. `yarn.lock` is the authoritative frontend lockfile. The existing `package-lock.json` is a retained legacy artifact, not package-manager authority. Do not regenerate or delete either lockfile as an incidental setup step.

The mandatory P0 frontend gate is frozen install plus build. Stable read-only lint and Vue SFC typecheck commands have not yet been established. The existing `lint-fix` command changes source and is not a read-only validation command. Read-only lint, Vue SFC typecheck, full browser E2E, and GitHub Actions are not mandatory P0 gates.

### Build artifacts and Git safety

Vite build generates `src/web/public/version-build` and `src/web/dist/`. Both are covered by the current ignore rules and must not enter the tracked diff. After validation, check:

```text
git diff --check
git status --short
```

A clean checkout must retain a clean tracked working tree after validation.

## P0 foundation status

P0 Foundation remediation is complete. The accepted foundation provides:

- Unified Action / Scope / Object / Field authorization.
- Transaction and database integrity safeguards.
- AuthSession and credential lifecycle management.
- Minimal operation traceability.
- Minimal private ManagedFile storage and authorized access.
- Reproducible foundation validation.

G1-G5 acceptance gates have passed. The current verified backend foundation baseline is **710 PASS**, with empty PostgreSQL migration, ORM smoke, Django checks, migration drift checks, ActionRegistry coverage, and production configuration tests also passing. Yarn frozen install and frontend build have passed without tracked changes. These results describe the accepted baseline; future changes must pass the applicable validation again.

Formal LIMS development may now proceed on top of the accepted foundation. Each LIMS module still requires its own Frozen Spec, business rules, migration review, tests, and UAT acceptance. Foundation completion does not mean that the LIMS application or its business modules are complete.

## Deferred engineering work

ESLint 9 configuration modernization, Vue SFC typecheck / `vue-tsc`, dual-lockfile cleanup, CI workflows, full E2E, and dependency modernization are not current P0 mandatory gates. Address them as needed before MVP or in later engineering work, under separately scoped tasks.
