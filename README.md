```markdown
# Name Profile API

A REST API that analyzes a given name using [Genderize.io](https://genderize.io), [Agify.io](https://agify.io), and [Nationalize.io](https://nationalize.io) to predict gender, age, and nationality. Results are stored in a PostgreSQL database.

## Live URL

```
https://stage1task-8e9a4akl2-abdirashidabubakar50s-projects.vercel.app
```

## Tech Stack

- **FastAPI** — web framework
- **SQLModel** — ORM (built on SQLAlchemy + Pydantic)
- **PostgreSQL** — database (Neon)
- **httpx** — async HTTP client for external APIs
- **Vercel** — deployment

## Project Structure

```
stage1_task/
├── app/
│   ├── api/
│   │   └── routes/
│   │       └── analyze.py       # all route handlers
│   ├── db/
│   │   └── session.py           # database engine and session
│   ├── models/
│   │   └── model.py             # SQLModel table definitions
│   ├── services/
│   │   └── classify.py          # age classification logic
│   └── main.py                  # app entry point, middleware, lifespan
├── vercel.json
├── requirements.txt
└── README.md
```

## Setup & Installation

```bash
# 1. Clone the repo
git clone https://github.com/your-username/stage1_task.git
cd stage1_task

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file
echo "DATABASE_URL=your_postgresql_connection_string" > .env

# 5. Run the development server
uvicorn app.main:app --reload
```

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string e.g. `postgresql://user:pass@host/db` |

## API Endpoints

### POST `/api/profiles`
Analyze a name and store the result.

**Request body:**
```json
{ "name": "john" }
```

**Response `201`:**
```json
{
  "status": "success",
  "data": {
    "id": "019da15d-732b-7f97-a433-4f6e74050b2a",
    "name": "john",
    "gender": "male",
    "gender_probability": 1.0,
    "sample_size": 2692560,
    "age": 75,
    "age_group": "senior",
    "country_id": "NG",
    "country_probability": 0.076,
    "created_at": "2026-04-18T16:12:29.355892"
  }
}
```

---

### GET `/api/profiles`
Retrieve all profiles with optional filters.

**Query params (all optional):**

| Param | Example |
|---|---|
| `gender` | `?gender=male` |
| `country_id` | `?country_id=NG` |
| `age_group` | `?age_group=senior` |

**Response `200`:**
```json
{
  "status": "success",
  "count": 2,
  "data": [ { ... }, { ... } ]
}
```

---

### GET `/api/profiles/{id}`
Retrieve a single profile by ID.

**Response `200`:**
```json
{
  "status": "success",
  "data": { ... }
}
```

**Response `404`:**
```json
{ "status": "404", "message": "Profile not found" }
```

---

### DELETE `/api/profiles/{id}`
Delete a profile by ID.

**Response:** `204 No Content`

---

## Error Responses

| Status | Meaning |
|---|---|
| `400` | Missing or empty name |
| `422` | Name must contain letters |
| `404` | Profile not found |
| `502` | External API returned invalid data |
| `504` | External API timed out |

**Error format:**
```json
{ "status": "502", "message": "Genderize returned an invalid response" }
```

## Age Groups

| Age Range | Group |
|---|---|
| 0 – 12 | `child` |
| 13 – 17 | `teenager` |
| 18 – 35 | `young adult` |
| 36 – 60 | `adult` |
| 60+ | `senior` |
```