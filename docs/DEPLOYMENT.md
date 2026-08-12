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
