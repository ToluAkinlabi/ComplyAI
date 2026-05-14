-- Optional seed file for Supabase local/dev environments.
-- For production, bootstrap admin/org is also seeded by backend startup when USE_DB_AUTH=true.

insert into organizations (name, slug)
values ('ComplyAI', 'complyai')
on conflict (slug) do nothing;
