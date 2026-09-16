# CompLIMS baseline setup

This document records the repository baseline setup established before the UI redesign and P0 remediation phases. It describes local configuration, sanitized initialization inputs, dependency-lockfile handling, and deployment safety constraints. Current project status is documented separately in Handover.md and the files under docs/.

- Backend: copy `src/backend/conf/env.example.py` to `env.py` in the same directory. The copy is ignored. Set `DJANGO_SECRET_KEY` and database credentials locally or through environment variables. There is no hardcoded signing-key fallback. Never commit the local file. Credentials previously present in source/local exports should be rotated before deployment.
- Frontend: copy `src/web/.env.example` to `.env`. Set non-secret Vite settings appropriate to each deployment. Local `.env.*` files are ignored. `VITE_*` values are public browser configuration, never credentials.
- Initialization inputs: local `init_users.json` and `init_systemconfig.json` under `src/backend/coreadmin/system/fixtures/` are excluded because they contain password hashes or a default password. Sanitized `.example.json` counterparts are provided. Copy them to their corresponding local names only when deliberately preparing initialization. Example users have unusable passwords (`!`); configure passwords through an appropriate local administration process. No database initialization or migration was performed for this baseline.
- Both existing frontend lockfiles (`package-lock.json` and `yarn.lock`) are preserved. Package-manager consolidation is deferred.
- Existing Django migrations, local FastCrud documentation, logos, and the design/review documents under `docs/` are part of the baseline.

Do not use the existing development security settings unchanged for a public deployment. Follow `docs/P0_REMEDIATION_PLAN.md` before starting formal LIMS development.
