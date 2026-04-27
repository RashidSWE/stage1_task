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

# Natural Language Query Parser

The `/api/profiles/search?q=` endpoint accepts plain English queries and converts
them into structured database filters using rule-based keyword matching — no AI or
external services involved.

---

## How It Works

The parser lowercases the query, then scans it in passes for gender, age group,
age range, and country. Each pass is independent, so filters combine freely:
`"young males from nigeria"` produces gender + age range + country all at once.

---

## Supported Keywords and Mappings

### Gender → `gender`

| Keywords | Filter |
|---|---|
| male, males, men, man, boy, boys | `gender=male` |
| female, females, women, woman, girl, girls | `gender=female` |
| "male and female" / both present | no gender filter (returns all) |

---

### Age Group → `age_group`

| Keywords | Filter |
|---|---|
| senior, elderly, old people | `age_group=senior` |
| adult, adults | `age_group=adult` |
| teenager, teenagers, teen, teens, adolescent | `age_group=teenager` |
| child, children, kid, kids | `age_group=child` |

> "young" is treated separately — it maps to `min_age=16 + max_age=24` and does
> not set `age_group`.

---

### Age Range → `min_age` / `max_age`

| Pattern | Example | Filter |
|---|---|---|
| above / over / older than N | "above 30" | `min_age=30` |
| below / under / younger than N | "under 18" | `max_age=18` |
| between N and M | "between 20 and 40" | `min_age=20, max_age=40` |
| young | "young males" | `min_age=16, max_age=24` |

---

### Country → `country_id`

Country names are matched using the `pycountry` library (249 countries).
The full country name must appear in the query. A 2-letter ISO code is used
as a fallback if no country name is found.

| Example | Filter |
|---|---|
| "from nigeria" | `country_id=NG` |
| "people in tanzania" | `country_id=TZ` |
| "adults from NG" | `country_id=NG` (ISO fallback) |

---

### Sorting → `sort_by` / `order`

| Keywords | Filter |
|---|---|
| "sort by age", "order by age" | `sort_by=age` |
| "recent", "latest", "newest" | `sort_by=created_at, order=desc` |
| "descending", "desc", "highest", "oldest" | `order=desc` |
| "ascending", "asc", "lowest", "youngest" | `order=asc` |

---

### Limit → `limit`

| Pattern | Example | Filter |
|---|---|---|
| top N / first N / limit N | "top 20 adults" | `limit=20` (max 50) |

---

## Example Mappings

| Query | Extracted Filters |
|---|---|
| `young males from nigeria` | `gender=male, min_age=16, max_age=24, country_id=NG` |
| `females above 30` | `gender=female, min_age=30` |
| `people from angola` | `country_id=AO` |
| `adult males from kenya` | `gender=male, age_group=adult, country_id=KE` |
| `male and female teenagers above 17` | `age_group=teenager, min_age=17` |
| `top 10 senior women in ghana` | `gender=female, age_group=senior, country_id=GH, limit=10` |

---

## Limitations and Known Edge Cases

### What the parser does not handle

- **Alternate spellings and typos** — `"nigria"`, `"kenya"`, `"femal"` will not
  match. The parser requires exact keyword matches.

- **Relative age terms beyond "young"** — words like `"middle-aged"`, `"mature"`,
  `"elderly men in their 60s"` are not mapped to any filter.

- **Age with units** — `"over thirty"` (written out) will not match. Only digit
  forms like `"over 30"` are supported.

- **Multiple countries** — `"people from nigeria or kenya"` will only match the
  first country found. There is no multi-country OR filter.

- **Negation** — `"not from nigeria"`, `"excluding males"` are not handled. The
  negative is ignored and the keyword still matches.

- **Compound conditions with OR** — `"males or females above 40"` will produce
  no gender filter (both genders detected) and `min_age=40`, which is correct
  by coincidence but not by design.

- **Common country name variants** — `"Congo"` may match the wrong country since
  both Democratic Republic of Congo and Republic of Congo exist. The parser picks
  whichever `pycountry` returns first.

- **Abbreviations and demonyms** — `"Nigerians"`, `"Kenyan women"`, `"a Ghanaian"`
  will not match. Only full official country names and ISO codes are supported.

- **Queries with no recognisable keywords** — return
  `{ "status": "error", "message": "Unable to interpret query" }`.

- **Pagination in natural language** — `"show me page 2"` or `"next 10"` are not
  parsed. Pagination must be passed explicitly via `page` and `limit` query params.

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