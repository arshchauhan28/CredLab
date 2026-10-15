# CredLab Production Deployment Guide (₹0 / Month Budget)

This guide provides a verified, zero-cost production deployment for **CredLab** using free tier services that require no paid infrastructure or credit cards.

---

## Architecture & Hosting Plan

| Component | Recommended Platform | Plan / Tier | Cost | Requirements |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | [Vercel](https://vercel.com) | Hobby Free Tier | ₹0 / mo | GitHub account |
| **Backend** | [Render](https://render.com) | Free Web Service | ₹0 / mo | GitHub account |
| **Database** | [Neon Postgres](https://neon.tech) / [Supabase](https://supabase.com) | Free Tier (0.5 GB) | ₹0 / mo | Free account |
| **Execution Sandbox** | [Judge0 CE Hosted](https://ce.judge0.com) | Public Community Tier | ₹0 / mo | None |

---

## 1. Database Setup (Neon PostgreSQL)

1. Sign up for free at [neon.tech](https://neon.tech) (no credit card required).
2. Create a new project (e.g. `credlab-db`), selecting your nearest AWS region (e.g., `ap-southeast-1` or `eu-central-1`).
3. Copy the pooled or direct connection string:
   ```
   postgresql://credlab_owner:<PASSWORD>@ep-xyz.neon.tech/credlab-db?sslmode=require
   ```
4. Note: SQLAlchemy 2.x requires the psycopg3 driver prefix:
   ```
   postgresql+psycopg://credlab_owner:<PASSWORD>@ep-xyz.neon.tech/credlab-db?sslmode=require
   ```

---

## 2. Backend Deployment (Render)

1. Push your CredLab repository to GitHub.
2. Sign up / Log in to [render.com](https://render.com).
3. Click **New +** -> **Web Service**.
4. Connect your GitHub repository.
5. Configure the service settings:
   - **Name:** `credlab-backend`
   - **Region:** Choose the region closest to your database (e.g. Oregon or Frankfurt).
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt && alembic upgrade head
     ```
   - **Start Command:**
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan:** `Free`
6. Add the following **Environment Variables** in the Render Dashboard:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Production mode |
| `DEBUG` | `false` | Disable debug logs/traces |
| `DATABASE_URL` | `postgresql+psycopg://...` | Neon connection string |
| `JWT_SECRET_KEY` | *(generate 32+ hex chars)* | `openssl rand -hex 32` |
| `JWT_ALGORITHM` | `HS256` | Standard signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token expiration |
| `JUDGE0_API_URL` | `https://ce.judge0.com` | Official hosted execution sandbox |
| `JUDGE0_TIMEOUT_SECONDS` | `15.0` | Execution timeout threshold |
| `JUDGE0_CPU_TIME_LIMIT` | `2.0` | Max sandbox CPU time per run |
| `JUDGE0_MEMORY_LIMIT_KB` | `128000` | Max sandbox memory (128 MB) |
| `EXECUTION_MOCK_MODE` | `false` | Enforce real sandbox execution |
| `BACKEND_CORS_ORIGINS` | `https://your-frontend.vercel.app` | Your deployed frontend domain |
| `CERTIFICATE_DEV_KEY_AUTOGEN` | `true` | Auto-generate signing keys if not injected |

7. Click **Create Web Service**. Render will install dependencies, apply Alembic migrations automatically, and start FastAPI.
8. Once live, note your backend URL: e.g. `https://credlab-backend.onrender.com`.
9. Verify health check: visit `https://credlab-backend.onrender.com/api/health`.

---

## 3. Frontend Deployment (Vercel)

1. Sign up / Log in to [vercel.com](https://vercel.com).
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository.
4. In the configuration screen:
   - **Root Directory:** Click `Edit` and select `frontend`.
   - **Framework Preset:** `Next.js`
   - **Build Command:** `npm run build` (default)
   - **Output Directory:** `.next` (default)
5. Under **Environment Variables**, add:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `API_BASE_URL` | `https://credlab-backend.onrender.com` | Your Render backend URL |

6. Click **Deploy**. Vercel will build the Next.js frontend with Turbopack and deploy it to a global CDN.
7. Note your frontend domain: e.g. `https://credlab.vercel.app`.
8. **IMPORTANT CORS UPDATE:** Return to your Render backend dashboard -> Environment Variables, and update `BACKEND_CORS_ORIGINS` to include your exact Vercel domain (e.g. `https://credlab.vercel.app`).

---

## 4. Alternative Execution Provider Configurations

CredLab's `Judge0Service` supports three deployment targets without changing code:

### Option A: Official Free Hosted Sandbox (Default)
```dotenv
JUDGE0_API_URL="https://ce.judge0.com"
JUDGE0_API_KEY=""
```
- 100% Free, no sign-up or card required.
- Verified to support Python, C, C++, and Java.
- Standard I/O and error diagnostics verified.

### Option B: RapidAPI Judge0 (Official Managed Cloud)
```dotenv
JUDGE0_API_URL="https://judge0-ce.p.rapidapi.com"
JUDGE0_API_KEY="<your-rapidapi-key>"
```
- CredLab automatically attaches `X-RapidAPI-Key` and `X-RapidAPI-Host` headers.

### Option C: Self-Hosted Judge0 (Linux VPS)
```dotenv
JUDGE0_API_URL="http://<your-vps-ip>:2358"
JUDGE0_API_KEY=""
```
- Run `docker compose up -d` on an Ubuntu 22.04+ VPS with Docker and cgroups v1/v2 support.

---

## 5. Post-Deployment Verification Checklist

1. **Backend Health Check:**
   `curl https://credlab-backend.onrender.com/api/health`
   Should return: `{"status": "healthy", "timestamp": "...", "version": "1.0.0"}`

2. **Frontend Connectivity Test:**
   Visit `https://credlab.vercel.app/api-test`
   Should display: `Backend status: healthy`

3. **Authentication:**
   - Register a Student or Admin account at `https://credlab.vercel.app/register/student`.
   - Verify login sets HttpOnly cookie `scp_session`.

4. **Code Execution:**
   - Open a practical assignment in the student workspace.
   - Run Python, C, C++, and Java with custom standard input (`2 2`).
   - Verify output displays `4`.
   - Submit for automated grading against test cases.
