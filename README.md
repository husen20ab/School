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

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | Yes | MongoDB Atlas connection string (set in Render.com environment variables) |
| `CORS_ORIGINS` | No | Comma-separated list of allowed origins (defaults to local dev origins; set Netlify domain for production) |

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

This project is configured for:
- **Backend**: Render.com (FastAPI)
- **Frontend**: Netlify (React)
- **Database**: MongoDB Atlas

### Step 1: Deploy Backend to Render.com

1. **Push your code to GitHub** (if not already done)

2. **Create a new Web Service on Render.com**:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml` configuration

3. **Configure the service** (or let `render.yaml` handle it):
   - **Name**: `school-app-backend` (or your preferred name)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`

4. **Set Environment Variables** in Render dashboard:
   - `MONGODB_URI`: `mongodb+srv://husen20ab_db_user:hOWWOtRx1cEg8jBw@cluster0.neidmqo.mongodb.net/`
   - `CORS_ORIGINS`: `https://school-logistics.netlify.app` (your Netlify domain)

5. **Deploy** - Render will build and deploy your backend
   - Note your backend URL (e.g., `https://school-app-backend.onrender.com`)

### Step 2: Deploy Frontend to Netlify

1. **Connect Netlify to GitHub**:
   - Go to [Netlify Dashboard](https://app.netlify.com)
   - Click "Add new site" → "Import an existing project"
   - Select your GitHub repository

2. **Configure build settings** (auto-detected from `netlify.toml`):
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `dist`

3. **Set Environment Variables** in Netlify dashboard:
   - Go to Site settings → Build & deploy → Environment
   - Add:
     - `VITE_API_BASE`: Your Render backend URL (e.g., `https://school-app-backend.onrender.com`)
     - Optional: `VITE_BG_URL`: Custom background image URL

4. **Deploy** - Netlify will build and deploy your frontend
   - Your frontend will be available at: `https://school-logistics.netlify.app`

### Step 3: Update CORS in Render (if not set in Step 1)

1. Go back to Render.com dashboard
2. Navigate to your backend service → Environment
3. Update `CORS_ORIGINS` to include your Netlify domain:
   ```
   https://school-logistics.netlify.app
   ```

4. **Redeploy** the backend service (Render will auto-redeploy on env var changes)

### Step 4: Verify Deployment

- Visit your Netlify URL: **https://school-logistics.netlify.app**
- Test creating/editing/deleting students
- Check backend health: `https://your-backend.onrender.com/health`
- View API docs: `https://your-backend.onrender.com/docs`

**Live Site**: [https://school-logistics.netlify.app](https://school-logistics.netlify.app)

---

**Note**: The MongoDB Atlas connection string is configured in `render.yaml` and will be set automatically when deploying via Render's Blueprint. You can also set it manually in the Render dashboard if needed.

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
├── requirements.txt       # Backend dependencies
├── render.yaml            # Render.com deployment configuration
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


