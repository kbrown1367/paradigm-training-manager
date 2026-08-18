# Paradigm Training Manager Deployment

## Production Architecture

Paradigm Training Manager is deployed as a single
same-origin web application:

Browser
  -> Render Web Service
     -> Gunicorn
        -> Flask
           -> PTM API
           -> React production build
     -> Render PostgreSQL

The Flask application serves both the operational API and
the compiled React application.

## Production Routes

API traffic remains under `/api`.

React routes include:

- `/`
- `/login`
- `/app`
- `/platform`

Unknown non-API routes fall back to the React entry point.
Unknown `/api/*` routes remain HTTP 404 responses.

## Database

Production uses PostgreSQL.

The Render PostgreSQL connection string is supplied through
`DATABASE_URL`.

PTM converts standard `postgresql://` connection strings to
SQLAlchemy's psycopg 3 form automatically.

The local SQLite database is development data and is not a
production datastore.

## Database Migrations

Database schema migrations are executed as a Render
pre-deploy step:

    cd backend && flask --app app db upgrade

Migrations are not run by each Gunicorn worker during
application startup.

## Database Backup and Recovery

PTM production data is stored in PostgreSQL. Database
recovery must therefore use PostgreSQL-native backup and
restore tooling rather than copying the local SQLite
development database.

### PostgreSQL Client Tools

The operational workstation used for backup or recovery must
have `pg_dump` and `pg_restore` available.

On macOS, PTM's scripts can automatically locate Homebrew's
keg-only `libpq` installation when it is installed with:

    brew install libpq

The tools do not need to be added permanently to `PATH`.

### Create a Backup

Use:

    scripts/backup_postgres.sh \
      "$DATABASE_URL" \
      backups/database

The second argument is an output directory, not a filename.

The script creates a timestamped PostgreSQL custom-format
archive such as:

    backups/database/ptm-postgres-YYYYMMDDTHHMMSSZ.dump

The backup script:

- requires a PostgreSQL database URL
- uses PostgreSQL custom archive format
- omits ownership and privilege commands
- refuses to report success if the archive is missing or empty

The resulting archive should be copied to secure storage
separate from the application and production database.

Do not commit database backups to Git.

### Validate a Backup

Before relying on an archive, inspect it with:

    pg_restore --list \
      backups/database/ptm-postgres-YYYYMMDDTHHMMSSZ.dump

A valid archive should produce a PostgreSQL archive table of
contents without an error.

### Restore a Backup

Restore is intentionally guarded because it can replace the
contents of the target database.

The restore command requires explicit authorization:

    PTM_ALLOW_RESTORE=YES \
    scripts/restore_postgres.sh \
      "$TARGET_DATABASE_URL" \
      backups/database/ptm-postgres-YYYYMMDDTHHMMSSZ.dump

The restore script uses:

- `--clean`
- `--if-exists`
- `--no-owner`
- `--no-privileges`
- `--exit-on-error`

Never point the restore command at production until the
target database and selected backup have been independently
confirmed.

When practical, restore to a disposable or isolated
PostgreSQL database first and verify the data before using
the procedure against production.

### Recovery Verification

Recovery is not considered complete merely because
`pg_restore` exits successfully.

After restoration:

1. connect to the restored database
2. verify expected agencies and administrators
3. verify representative employee and training records
4. verify the Alembic revision
5. start PTM against the restored database
6. verify authentication and tenant isolation
7. verify agency dashboards and compliance calculations

For command-line SQL verification, use PostgreSQL's
`ON_ERROR_STOP` option so SQL validation failures produce a
nonzero command status:

    psql \
      -v ON_ERROR_STOP=1 \
      -P pager=off \
      "$TARGET_DATABASE_URL"

### Recovery Drill Validation

During the v0.6.1 production-hardening work, the PTM backup
and restore procedure was exercised against a disposable
PostgreSQL 17 database.

The validation procedure:

1. created known records
2. created a custom-format backup with the PTM backup script
3. verified the backup archive with `pg_restore --list`
4. deliberately modified and deleted source records
5. restored the archive with the PTM restore script
6. verified that the original records and values were
   recovered exactly

This demonstrated the operational backup/restore path
without modifying PTM production data.

A production recovery drill should be repeated periodically
and after material changes to database infrastructure or
recovery tooling.

## Production Server

Render starts PTM with Gunicorn.

The Flask development server in `backend/run.py` remains for
local development only.

## Required Production Configuration

Render supplies or configures:

- `DATABASE_URL`
- `SECRET_KEY`
- `PTM_ENV=production`
- `SESSION_COOKIE_SECURE=true`
- `PYTHON_VERSION`
- `NODE_VERSION`

PTM refuses to start in production without `SECRET_KEY`.

## Build

The Render build performs:

1. Python dependency installation
2. deterministic frontend dependency installation using
   `npm ci`
3. Vite production build

The resulting `frontend/dist` directory is served by Flask.

## Initial Production Provisioning

A new production database begins empty.

After the first successful deployment and migration:

1. create the Paradigm platform administrator
2. sign in through `/login`
3. create agencies through Platform Administration
4. create agency administrators through Platform
   Administration
5. have each agency import its four TCOLE reports

Do not copy the local development SQLite database into
production unless a deliberate data migration is designed
and validated.

## Pilot Acceptance Test

Before inviting external agencies, verify:

- public landing page loads
- `/login` loads directly
- `/app` redirects unauthenticated users
- `/platform` enforces platform-admin access
- platform administrator can create an agency
- multiple administrators can exist for one agency
- agency administrators see only their agency
- TCOLE four-file import succeeds
- subsequent imports preserve personnel
- archived employees remain archived after re-import
- employee archive and restore work
- dashboard and compliance calculations load
- logout destroys the authenticated session
