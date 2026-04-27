# 🔍 Can I Trust? — AI-Powered Fake News Detector

> Ek complete full-stack project jo BERT/DistilBERT model use karke news articles ko real ya fake classify karta hai.

---

## 📁 Project Structure

```
can_i_trust_complete/
├── backend/              ← FastAPI Python backend
│   ├── app/
│   │   ├── main.py          ← App entry point
│   │   ├── core/            ← Config, DB, Redis, Security
│   │   ├── api/routes/      ← Auth, Analyze, News endpoints
│   │   ├── models/          ← SQLAlchemy DB models
│   │   ├── schemas/         ← Pydantic request/response schemas
│   │   ├── services/        ← Business logic
│   │   └── ml/              ← ML model service
│   ├── scripts/train_model.py  ← Model training script
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/             ← React + Vite frontend
│   ├── src/
│   │   ├── App.jsx          ← Main app with routing
│   │   ├── pages/           ← Login, Dashboard, Checker, History
│   │   ├── components/      ← Navbar, shared components
│   │   ├── services/api.js  ← Axios API calls
│   │   └── store/           ← Zustand state management
│   ├── package.json
│   └── vite.config.js
│
├── docker/               ← Docker deployment setup
│   ├── docker-compose.yml       ← Production
│   ├── docker-compose.dev.yml   ← Development
│   ├── backend/Dockerfile
│   ├── frontend/Dockerfile
│   ├── nginx/               ← Reverse proxy config
│   ├── scripts/             ← DB init, Redis config, backups
│   ├── Makefile             ← Handy commands
│   └── setup.sh             ← One-click setup
│
└── model_training/       ← ML training scripts + datasets
    ├── train_model.py       ← Main BERT training script
    ├── evaluate_model.py    ← Model evaluation
    ├── Fake.csv             ← ISOT fake news dataset
    ├── True.csv             ← ISOT real news dataset
    └── requirements_ml.txt
```

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
cd docker/
cp .env.example .env
# .env file mein apni values bharo (SECRET_KEY, NEWS_API_KEY, etc.)
nano .env

docker-compose up -d
# Frontend: http://localhost
# Backend API: http://localhost/api/v1
# API Docs: http://localhost/api/v1/docs
```

### Option 2: Local Development

**Backend:**
```bash
cd backend/
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env mein database aur redis URLs set karo

uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend/
npm install
cp .env.example .env  # VITE_API_URL=http://localhost:8000
npm run dev
# Opens at http://localhost:5173
```

---

## 🤖 ML Model Training

```bash
cd model_training/
pip install -r requirements_ml.txt

# ISOT dataset (Fake.csv + True.csv) already included!
python train_model.py \
  --fake Fake.csv \
  --true True.csv \
  --output ../backend/app/ml_models/fake_news_model \
  --epochs 3

# Quick smoke test (500 samples):
python train_model.py --quick
```

**Training details:**
- Base model: `distilbert-base-uncased` (~250MB)
- Dataset: ISOT (44,898 articles) + optional LIAR dataset
- Labels: 0 = Fake, 1 = Real
- Output: `backend/app/ml_models/fake_news_model/`

---

## 🔑 Environment Variables

**Backend `.env`:**
```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/can_i_trust
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-super-secret-key-32-chars-min
NEWS_API_KEY=your_newsapi_org_key
MODEL_PATH=./app/ml_models/fake_news_model
```

**Frontend `.env`:**
```
VITE_API_URL=http://localhost:8000
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, get JWT tokens |
| GET  | `/api/v1/auth/me` | Current user profile |
| POST | `/api/v1/analyze/text` | Analyze text |
| POST | `/api/v1/analyze/url` | Analyze URL |
| POST | `/api/v1/analyze/image` | Analyze image (OCR) |
| GET  | `/api/v1/analyze/history` | Check history |
| GET  | `/api/v1/news/trending` | Trending news |
| GET  | `/api/v1/news/search?q=query` | Search news |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11, SQLAlchemy, Alembic |
| ML | HuggingFace Transformers, DistilBERT, PyTorch |
| Database | PostgreSQL (async via asyncpg) |
| Cache | Redis |
| Frontend | React 18, Vite, Zustand, Axios |
| Deployment | Docker, Nginx, Gunicorn + Uvicorn |
| Auth | JWT (python-jose), bcrypt |
| OCR | Tesseract + pytesseract |

---

## 🔧 Docker Makefile Commands

```bash
cd docker/
make up       # Start all services
make down     # Stop all services
make logs     # View logs
make ps       # Service status
make restart  # Restart services
make db-shell # Open PostgreSQL shell
```
