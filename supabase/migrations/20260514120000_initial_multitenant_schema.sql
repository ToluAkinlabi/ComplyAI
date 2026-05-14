-- ComplyAI initial multi-tenant schema for Supabase Postgres

create table if not exists organizations (
  id bigserial primary key,
  name varchar(120) not null,
  slug varchar(120) not null unique,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_organizations_slug on organizations(slug);

create table if not exists users (
  id bigserial primary key,
  email varchar(255) not null unique,
  full_name varchar(120),
  hashed_password varchar(255) not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_users_email on users(email);

create table if not exists organization_memberships (
  id bigserial primary key,
  organization_id bigint not null references organizations(id) on delete cascade,
  user_id bigint not null references users(id) on delete cascade,
  role varchar(32) not null default 'member',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  constraint uq_org_user unique (organization_id, user_id)
);

create index if not exists idx_org_memberships_org_id on organization_memberships(organization_id);
create index if not exists idx_org_memberships_user_id on organization_memberships(user_id);

create table if not exists compliance_reports (
  id bigserial primary key,
  organization_id bigint references organizations(id) on delete set null,
  created_by_user_id bigint references users(id) on delete set null,
  client_name varchar(100) not null,
  document_name varchar(255) not null,
  report_data jsonb,
  report_file_name varchar(255),
  json_file_name varchar(255),
  status varchar(32) not null default 'completed',
  error_message text,
  created_at timestamptz not null default now(),
  file_size bigint,
  processing_time integer
);

create index if not exists idx_reports_org_id on compliance_reports(organization_id);
create index if not exists idx_reports_created_by on compliance_reports(created_by_user_id);
create index if not exists idx_reports_created_at on compliance_reports(created_at desc);
create index if not exists idx_reports_pdf_name on compliance_reports(report_file_name);
create index if not exists idx_reports_json_name on compliance_reports(json_file_name);
