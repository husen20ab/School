# School Students App

Full-stack CRUD application for managing students and their enrolled courses.  
Backend: FastAPI + MongoDB.  
Frontend: React (Vite) with Netlify-ready configuration.

---

## Quick Start (Local Development)

### Backend
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.app.txt
uvicorn main:app --reload
```
Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URL` | `mongodb://localhost:27017` | Mongo connection string |
| `MONGO_DB` | `school` | Database name |
| `CORS_ORIGINS` | local dev origins | Comma-separated list of allowed origins (set Netlify domain here for production) |

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Optional `frontend/.env.local`:
```
VITE_API_BASE=http://localhost:8000
VITE_BG_URL=https://example.com/your-school-campus.jpg
```

---

## Production Deployment

### 1. Backend (FastAPI)
Deploy to your preferred platform (Render, Railway, Fly.io, etc.) with:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Set environment variables:
- `MONGO_URL` and `MONGO_DB`
- `CORS_ORIGINS` — include Netlify domain, e.g. `https://your-site.netlify.app`

Recommended hardening:
- Run behind HTTPS (reverse proxy or managed load balancer)
- Enable process supervision (systemd, gunicorn+uvicorn workers, etc.)
- Configure logging/monitoring and database backups

### 2. Frontend (Netlify)

`netlify.toml` already targets the `frontend/` directory:
```toml
[build]
  base = "frontend"
  command = "npm run build"
  publish = "dist"
```

Steps:
1. Connect Netlify to this repository.
2. Set environment variables in the Netlify dashboard:
   - `VITE_API_BASE=https://your-backend-domain`
   - Optional `VITE_BG_URL=https://example.com/your-school-campus.jpg`
3. Deploy – Netlify will run `npm run build` and publish `dist/`.

SPA routing is handled via `frontend/public/_redirects` (`/* /index.html 200`).

---

## Testing & Quality

- API validation uses Pydantic models (`StudentIn`, `StudentOut`).
- Add your own tests (e.g. `pytest`) and CI pipeline before production cutover.
- For linting, consider ESLint/Prettier (frontend) and Ruff/Black (backend).

---

## Customization

- **Background image**: Set `VITE_BG_URL` to a school-specific branded photo.
- **Brand colors & typography**: Adjust CSS variables in `frontend/src/styles.css`.
- **API authentication**: Add security (JWT/session) before exposing publicly.

---

## Project Structure

```
my-env/
├── main.py                # FastAPI application
├── requirements.app.txt   # Backend dependencies
├── netlify.toml           # Netlify build configuration
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── public/
│   │   └── _redirects
│   └── vite.config.js
└── README.md
```


