# Simple Supabase full-stack demo

This demo includes:
- a **simple backend** (`backend.py`)
- a **simple frontend** (`static/index.html`)
- a **database connection to Supabase** via PostgREST

## 1) Create table in Supabase

Run this SQL in the Supabase SQL editor:

```sql
create table if not exists public.todos (
  id bigint generated always as identity primary key,
  title text not null,
  is_done boolean not null default false,
  created_at timestamp with time zone not null default now()
);
```

If you use RLS, add policies that allow reads/inserts for your chosen key.

## 2) Set environment variables

```bash
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_ANON_KEY="<your-anon-or-service-role-key>"
export SUPABASE_TABLE="todos"
```

## 3) Run the app

```bash
python examples/supabase_fullstack/backend.py
```

Open `http://localhost:8000`.

## API endpoints

- `GET /api/health`
- `GET /api/todos`
- `POST /api/todos` with body `{ "title": "Buy milk" }`
