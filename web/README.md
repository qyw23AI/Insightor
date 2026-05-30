# Insightor Web Console

AI-Powered PR Review Web Console — FastAPI backend + React/Vite frontend.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20.x
- Insightor installed: `pip install -e ".[web]"` (from project root)

### Development Mode

```bash
# Terminal 1: Backend
cd /path/to/Insightor
uvicorn web.backend.app:app --reload --port 8000

# Terminal 2: Frontend
cd web/frontend
npm install
npm run dev
# → http://localhost:5173  (API proxy auto-forwards to :8000)
```

### Production Mode

```bash
cd web/frontend && npm run build
cd .. && uvicorn web.backend.app:app --host 0.0.0.0 --port 80
# → http://<server-ip>/
```

### Default Admin Account

- Username: `admin`
- Password: `admin123`
- Change after first login!

### Initialize Database

```bash
python -m web.backend.seed
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | No | Health check |
| POST | `/api/auth/register` | No | Register new user |
| POST | `/api/auth/login` | No | Login, returns JWT |
| GET | `/api/auth/me` | Yes | Current user info |
| GET | `/api/admin/users` | Admin | List all users |
| DELETE | `/api/admin/users/{id}` | Admin | Delete a user |
| GET | `/api/config` | Yes | Get user config (decrypted) |
| GET | `/api/config/masked` | Yes | Get config (masked for display) |
| PUT | `/api/config` | Yes | Save config |
| GET | `/api/pr/entries` | Yes | List saved PRs |
| POST | `/api/pr/entries` | Yes | Add PR URLs |
| DELETE | `/api/pr/entries/{id}` | Yes | Delete PR entry |
| POST | `/api/analyze` | Yes | Start analysis |
| GET | `/api/analyze/{job_id}/stream` | No | SSE progress stream |
| GET | `/api/analyze/{job_id}/result` | No | Get analysis result |
| GET | `/api/reviews` | Yes | List reviews |
| GET | `/api/reviews/{id}` | Yes | Get review detail |
| GET | `/api/reviews/{id}/diff` | Yes | Get review diff |
| POST | `/api/reviews/{id}/publish` | Yes | Publish feedback |
| DELETE | `/api/reviews/{id}` | Yes | Delete review |

## Architecture

```
web/
├── backend/           # FastAPI (Python)
│   ├── app.py         # App factory
│   ├── auth.py        # JWT + bcrypt
│   ├── database.py    # SQLAlchemy async + SQLite
│   ├── models.py      # ORM models
│   ├── encryption.py  # Fernet encryption
│   ├── sse_manager.py # SSE pub/sub
│   ├── job_manager.py # Pipeline wrapper
│   ├── seed.py        # DB init
│   └── routes/        # API endpoints
├── frontend/          # React + Vite + Tailwind
│   └── src/
│       ├── components/ # Reusable UI components
│       ├── pages/      # Page components
│       ├── hooks/      # useSSE, etc.
│       ├── api/        # API client
│       ├── types/      # TypeScript URF types
│       └── context/    # Auth context
└── README.md
```

## Security

- API keys and tokens are encrypted with Fernet (symmetric encryption)
- Key stored in `.insightor/.fernet_key` (auto-generated on first use)
- Passwords hashed with bcrypt
- JWT tokens expire after 72 hours
