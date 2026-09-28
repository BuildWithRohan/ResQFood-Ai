# ResQFood AI

**"Predict. Prevent. Allocate. Rescue."**

AI-powered food waste prevention and redistribution platform for institutional kitchens, NGOs, and delivery operators.

## Three Core Innovations

1. **Predictive Prevention** — ML-based demand prediction to reduce unnecessary overproduction
2. **Intelligent Allocation** — OR-Tools constrained optimization for fair, explainable food distribution
3. **Time-Aware Rescue** — Ensures food reaches recipients before its usable window expires

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite |
| Backend | Python FastAPI |
| Database | PostgreSQL (SQLite fallback) |
| ML | scikit-learn (GradientBoostingRegressor) |
| Optimization | Google OR-Tools (CP-SAT solver) |
| Communication | Twilio WhatsApp API |

---

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp ../.env.example ../.env
# Edit .env with your DATABASE_URL if using PostgreSQL

# Seed demo data
python -m seed.seed_data

# Start backend
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 3. Access

- **Frontend**: http://localhost:5173
- **Backend API Docs**: http://localhost:8000/docs

---

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@resqfood.ai | admin123 |
| Kitchen | kitchen@abccollege.edu | kitchen123 |
| NGO A | ngo_a@feedindia.org | ngoa123 |
| NGO B | ngo_b@mealshare.org | ngob123 |
| NGO C | ngo_c@foodrescue.in | ngoc123 |
| Driver | driver@resqfood.ai | driver123 |

---

## Demo Walkthrough

### Step 1: Predictive Prevention
Login as **Kitchen** → View ML demand prediction:
- Historical average: ~800 meals/day
- Predicted demand: ~720 meals
- Recommended production: ~735 meals
- Potential overproduction avoided: ~65 meals

### Step 2: Surplus Registration
Kitchen registers 40 meals of Vegetable Biryani with 3-hour usable window.

### Step 3: NGO Requests (Competing)
Three NGOs request food:
- NGO A → 15 meals (High urgency)
- NGO B → 30 meals (Medium urgency)
- NGO C → 10 meals (Very High urgency)
- **Total: 55 meals requested, only 40 available**

### Step 4: Smart Allocation
Navigate to Allocation page → Run Smart Allocation Engine:
- OR-Tools optimizes distribution considering urgency, distance, time, capacity
- Each allocation includes explainable reasoning
- Factor chips show why each decision was made

### Step 5: Delivery Route
Create delivery → Route optimizer sequences stops by urgency and proximity.

### Step 6–8: Driver Pickup → Delivery → OTP Verification
Login as **Driver** → Start delivery → Mark arrivals → Verify OTP at each stop.

### Step 9: Impact Dashboard
Login as **Admin** → View updated metrics: meals rescued, weight redistributed, estimated environmental impact.

---

## API Documentation

Interactive API docs available at `http://localhost:8000/docs` when the backend is running.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/login | User authentication |
| POST | /api/demand/predict | Run ML demand prediction |
| POST | /api/surplus/ | Register surplus food |
| POST | /api/requests/ | Submit food request |
| POST | /api/allocation/run | Run Smart Allocation Engine |
| POST | /api/deliveries/ | Create optimized delivery |
| POST | /api/deliveries/{id}/stops/{sid}/verify-otp | Verify delivery OTP |
| GET | /api/analytics/impact | Impact metrics |

---

## Project Structure

```
resqfood-ai/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI route handlers
│   │   ├── models/        # SQLAlchemy database models
│   │   ├── schemas/       # Pydantic validation schemas
│   │   ├── services/      # Business logic services
│   │   ├── ml/            # ML demand prediction engine
│   │   ├── optimization/  # OR-Tools allocation & routing
│   │   ├── main.py        # FastAPI application entry
│   │   ├── config.py      # Configuration management
│   │   └── database.py    # Database connection
│   ├── seed/              # Demo data seeding
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/         # Role-based dashboard pages
│   │   ├── components/    # Shared UI components
│   │   └── services/      # API client
│   └── package.json
├── .env.example
└── README.md
```

---

## License

MIT
