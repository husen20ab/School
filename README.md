# School Students App

Full-stack CRUD application for managing students and their enrolled courses.  
Backend: FastAPI + MongoDB.  
Frontend: React (Vite) with Netlify-ready configuration.

## 🚀 Live URLs

- **Frontend**: [https://school-logistics.netlify.app](https://school-logistics.netlify.app)
- **Backend API**: [https://school-0a5y.onrender.com](https://school-0a5y.onrender.com)
- **API Docs**: [https://school-0a5y.onrender.com/docs](https://school-0a5y.onrender.com/docs)
- **Health Check**: [https://school-0a5y.onrender.com/health](https://school-0a5y.onrender.com/health)

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
# Or use production backend: VITE_API_BASE=https://school-0a5y.onrender.com
VITE_BG_URL=https://example.com/your-school-campus.jpg
```

## Authentication

| Username | Password | Role  | Notes                                                                 |
|----------|----------|-------|-----------------------------------------------------------------------|
| `admin`  | `admin`  | admin | Full access to all features, including health check and API docs      |
| `john`   | `john`   | user  | Limited access – cannot open health, list JSON, OpenAPI Docs, or ReDoc |

- Use the built-in login screen (calming nature background) to authenticate.
- The frontend stores a short-lived token in `localStorage`.
- All API calls require `Authorization: Bearer <token>` and go through `/api/login`.
- Admin-only pages (`/health`, `/docs`, `/redoc`) require admin credentials.

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
   - Your backend URL: **https://school-0a5y.onrender.com**

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
     - `VITE_API_BASE`: `https://school-0a5y.onrender.com`
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
- Check backend health: **https://school-0a5y.onrender.com/health**
- View API docs: **https://school-0a5y.onrender.com/docs**

**Live Site**: [https://school-logistics.netlify.app](https://school-logistics.netlify.app)  
**Backend API**: [https://school-0a5y.onrender.com](https://school-0a5y.onrender.com)

---

**Note**: The MongoDB Atlas connection string is configured in `render.yaml` and will be set automatically when deploying via Render's Blueprint. You can also set it manually in the Render dashboard if needed.

---

## Troubleshooting

### Internal Server Error on `/api/students`

If you're getting a 500 error, check:

1. **Verify MongoDB URI in Render**:
   - Go to Render Dashboard → Your Service → Environment
   - Ensure `MONGODB_URI` is set to: `mongodb+srv://husen20ab_db_user:hOWWOtRx1cEg8jBw@cluster0.neidmqo.mongodb.net/`
   - If missing, add it and redeploy

2. **Check MongoDB Atlas Network Access**:
   - Go to MongoDB Atlas → Network Access
   - Add IP Address: `0.0.0.0/0` (allow all) or add Render.com IPs
   - Wait a few minutes for changes to propagate

3. **Check Health Endpoint**:
   - Visit: `https://school-0a5y.onrender.com/health`
   - Should return: `{"status": "ok", "database": "connected"}`
   - If it shows an error, check Render logs for details

4. **Check Render Logs**:
   - Go to Render Dashboard → Your Service → Logs
   - Look for MongoDB connection errors

### Netlify Frontend Not Showing Students

If the frontend loads but shows no students:

1. **Verify `VITE_API_BASE` in Netlify**:
   - Go to Netlify Dashboard → Your Site → Site settings → Build & deploy → Environment
   - Ensure `VITE_API_BASE` is set to: `https://school-0a5y.onrender.com`
   - **Important**: After adding/updating, you must trigger a new deploy
   - Go to Deploys → Trigger deploy → Deploy site

2. **Check Browser Console**:
   - Open browser DevTools (F12) → Console tab
   - Look for errors or check what URL it's trying to fetch
   - Should see: `Fetching students from: https://school-0a5y.onrender.com/api/students`
   - If it shows a relative path like `/api/students`, the env var is not set

3. **Verify CORS is Working**:
   - Check browser Network tab for failed requests
   - CORS errors will show in console as "blocked by CORS policy"
   - **Note**: The Netlify domain is now hardcoded in the backend code, so CORS should work automatically
   - If you still get CORS errors, redeploy the backend on Render.com

4. **Test Backend Directly**:
   - Visit: `https://school-0a5y.onrender.com/api/students`
   - Should return JSON array (even if empty: `[]`)
   - If this works but frontend doesn't, it's a CORS or env var issue

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


