# Supabase README

Supabase/Postgres schema, migrations, RLS policies, and development seed data for Ellenor Events.

## Files

- `schema.sql`: consolidated schema reference.
- `migrations/`: versioned SQL migrations, applied in timestamp order.
- `seed.sql`: deterministic demo data for QA/staging.

## Apply Migrations

```bash
for file in supabase/migrations/*.sql; do
  psql "$DATABASE_URL" -f "$file"
done
```

With Supabase CLI after linking a hosted project:

```bash
supabase db push
```

## Seed Data

Use seed data in local/staging only:

```bash
psql "$DATABASE_URL" -f supabase/seed.sql
```

Seed highlights:

- `Amina Owner` owns both demo events.
- `David Partner` is partner on both demo events.
- `Grace Chair` is committee chair with summary budget visibility.
- `Sarah Viewer` has contribution-only visibility on the introduction.
- Introduction project ID: `10000000-0000-0000-0000-000000000001`.
- Wedding project ID: `10000000-0000-0000-0000-000000000002`.

## Migration Rules

- Never edit applied migrations after they are pushed to a shared environment.
- Add new migration files for schema changes.
- Keep backend SQLAlchemy models and Pydantic schemas aligned.
- Keep RLS policies project-scoped.
- Do not seed real personal data into production.
