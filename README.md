# Krishna Daily Life OS

A production-style Django personal daily-life management app for habits, tasks, expenses, credit card bill reminders, subscriptions, study tracking, and reports.

## Features

- Login, register, logout, and profile pages
- Data stored per user
- Tracks habits the user adds manually or imports from a file after the selected tracking start date
- Mark habits and to-dos complete or pending
- Daily habit score percentage
- Last 7 days habit report
- Monthly expense report
- Current cash and bank balances after expenses
- Study minutes report
- Credit card reminders 5 days before due date
- Subscription renewal reminders
- Mobile-friendly Bootstrap 5 UI
- Django admin support
- SQLite locally and PostgreSQL in production
- Docker, Gunicorn, WhiteNoise, and `.env` configuration

## Local Setup

```bash
cd /Users/mandadimahendharreddy/krishna_daily_life_os
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Docker Setup

Create `.env` from the example:

```bash
cp .env.example .env
```

For Docker with PostgreSQL, set this in `.env`:

```text
DATABASE_URL=postgres://postgres:postgres@db:5432/krishna_daily_life_os
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
```

Run:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8000/
```

Create a superuser inside Docker:

```bash
docker compose exec web python manage.py createsuperuser
```

## PostgreSQL Setup Without Docker

Create a database:

```sql
CREATE DATABASE krishna_daily_life_os;
CREATE USER krishna_user WITH PASSWORD 'strong-password';
GRANT ALL PRIVILEGES ON DATABASE krishna_daily_life_os TO krishna_user;
```

Set `.env`:

```text
DATABASE_URL=postgres://krishna_user:strong-password@localhost:5432/krishna_daily_life_os
```

Run:

```bash
python manage.py migrate
python manage.py runserver
```

## Migrations

After changing models:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Admin Panel

Create an admin user:

```bash
python manage.py createsuperuser
```

Open:

```text
http://127.0.0.1:8000/admin/
```

## Deployment Notes

Production environment variables:

```text
SECRET_KEY=your-production-secret
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-app.onrender.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://your-app.onrender.com
DATABASE_URL=your-postgres-url
SECURE_SSL_REDIRECT=False
```

Use `SECURE_SSL_REDIRECT=True` only after HTTPS and proxy headers are confirmed on your hosting provider.

## Deploy to Render

Render can run this app on a free web service with a free PostgreSQL database.
The free web service sleeps after idle time, and Render free PostgreSQL databases
expire after 30 days. Use a paid database, another PostgreSQL provider, or regular
exports if this will hold important long-term data.

1. Push this project to GitHub.
2. Sign in to Render.
3. Open **Blueprints** and create a new Blueprint instance.
4. Select this repository.
5. Render reads `render.yaml`, creates the web service and PostgreSQL database,
   then runs `build.sh`.
6. Open the generated `https://krishna-daily-life-os.onrender.com` style URL.

Manual Render setup also works:

- Build command:

```bash
./build.sh
```

- Start command:

```bash
gunicorn config.wsgi:application
```

- Environment variables:

```text
DEBUG=False
SECRET_KEY=<generated secret>
DATABASE_URL=<Render PostgreSQL internal database URL>
SECURE_SSL_REDIRECT=False
```

## Deploy to Railway, Fly.io, or AWS

Use the included `Dockerfile`.

General steps:

1. Create a PostgreSQL database on the platform.
2. Set environment variables from `.env.example`.
3. Set `DEBUG=False`.
4. Set `DATABASE_URL` to the platform PostgreSQL URL.
5. Deploy the Docker image.
6. Run migrations during release or manually:

```bash
python manage.py migrate
```

## Access From Mobile After Deployment

After deployment, open your deployed URL from any mobile browser:

```text
https://your-app-domain.com
```

Register/login with your account. Each user's data is private and filtered by login.

For local mobile testing on the same Wi-Fi:

```bash
python manage.py runserver 0.0.0.0:8000
```

Find your laptop IP address, then open this on your phone:

```text
http://YOUR-LAPTOP-IP:8000/
```

Add your laptop IP to `.env`:

```text
ALLOWED_HOSTS=localhost,127.0.0.1,YOUR-LAPTOP-IP
```

## Project Structure

```text
krishna_daily_life_os/
  config/                 Django project settings
  lifeos/                 Main application
  templates/              Django templates
  static/                 CSS and static assets
  requirements.txt
  Dockerfile
  docker-compose.yml
  render.yaml
  .env.example
```
