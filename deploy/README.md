# Deployment Notes

## Current target

This repo is now prepared for a `LAN multi-user` deployment model:

- Frontend is expected to be built with `npm run build`
- `Nginx` serves the built frontend and reverse-proxies `/api` to FastAPI
- File-heavy workflows use browser upload/download instead of server-side path browsing

## Recommended layout

- Frontend build output: `/srv/detect-report/frontend/dist`
- Backend process: `uvicorn backend.main:app --host 127.0.0.1 --port 8000`
- Nginx config example: [`deploy/nginx/detect-report.conf`](./nginx/detect-report.conf)

## Backend env

Set allowed browser origins with:

```bash
BACKEND_CORS_ORIGINS=http://192.168.1.20,https://reports.example.com
```

If frontend and backend are both behind the same Nginx site, the browser will usually hit the same origin and CORS becomes much simpler.

## Deployment steps

1. Build frontend:

```bash
cd frontend
npm run build
```

2. Start backend:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

3. Point Nginx `root` to `frontend/dist` and proxy `/api/` to `127.0.0.1:8000`.

4. For public deployment, add HTTPS and a fixed `server_name`.

## Remaining risks

- Database is still SQLite. It is acceptable for low-write LAN usage, but PostgreSQL should be the next infrastructure upgrade before higher concurrency or public internet usage.
- There is still no full auth layer here. Do not expose this service publicly without authentication, HTTPS, and network restrictions.
