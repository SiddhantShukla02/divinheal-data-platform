# Local Setup

This document explains how to set up the Divinheal Data Platform locally.

The project is currently in initial setup. No production scraper, database schema, migration system, or source pipeline has been implemented yet.

## Requirements

- Python 3.11 or newer
- Git
- Local Postgres
- Optional: VS Code or another editor

## Clone / open the repo

If the remote GitHub repository already exists:

```bash
git clone <repo-url>
cd divinheal-data-platform
```

If working locally before the remote repo exists, open the existing project folder directly.

## Create a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

After activation, the terminal should show `(.venv)`.

## Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Environment variables

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Then adjust `.env` if needed.

The important variable is:

```env
DATABASE_URL=postgresql://divinheal:divinheal_dev_password@localhost:5433/divinheal_data
```

Use the correct port, username, password, and database name for the local Postgres setup.

## Local Postgres

This project uses Postgres for structured data.

For local development, Postgres may be installed directly on the machine or run through Docker.

The application should connect using `DATABASE_URL`.

No tables, migrations, or seed scripts have been created yet.

## Data folders

Local artifact folders are under:

```text
data/raw/
data/normalized/
data/errors/
data/local/
```

Raw and generated data files are ignored by Git, except `.gitkeep` placeholders.

## Current status

At this stage, setup only verifies that the Python project structure exists.

Scraper implementation, database migrations, and source pipelines will be added in later steps.
```