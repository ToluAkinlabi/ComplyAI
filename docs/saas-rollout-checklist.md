# ComplyAI SaaS Rollout Checklist

This checklist turns the current single-tenant prototype into a production-grade SaaS platform in phases.

## Phase 0: Foundations (Completed in this change)

- [x] Add core data models for multi-tenant entities: organizations, users, memberships.
- [x] Add report model fields for tenant/user attribution.
- [x] Add database session bootstrap (`DATABASE_URL`, SQLite by default).
- [x] Seed bootstrap admin identity and default organization.
- [x] Switch login to persistence-backed authentication with fallback support.
- [x] Add token claims for `org_id` and `user_id`.

## Phase 1: Tenant Isolation

- [ ] Store generated reports with `organization_id` and `created_by_user_id`.
- [ ] Replace filesystem-only report listing with DB-indexed report registry.
- [ ] Enforce object-level authorization: user can access only org-owned reports.
- [ ] Remove shared report namespace patterns in API responses.

Definition of done:

- Cross-tenant report access is impossible by URL guessing.

## Phase 2: Identity and Access Management

- [ ] Add user registration and invitation flow per organization.
- [ ] Add password reset flow and account lockout policy.
- [ ] Add role matrix (`owner`, `admin`, `analyst`, `viewer`) with endpoint-level checks.
- [ ] Add refresh-token lifecycle and revocation strategy.

Definition of done:

- Every authenticated action is attributable to a user and org.

## Phase 3: Async Processing and Reliability

- [ ] Persist analysis jobs in DB with states (`queued`, `running`, `completed`, `failed`).
- [ ] Route heavy analysis to Celery worker queue.
- [ ] Add retry strategy, dead-letter handling, and status polling endpoints.
- [ ] Add idempotency key for upload requests.

Definition of done:

- Large jobs are resilient to worker/process restarts.

## Phase 4: Billing and Usage

- [ ] Define usage dimensions: document count, pages analyzed, recommendation tokens.
- [ ] Add subscription plans and quotas by organization.
- [ ] Add hard and soft limits with clear API error semantics.
- [ ] Implement billing event pipeline (invoice-safe audit trail).

Definition of done:

- Usage can be measured, limited, and billed per tenant.

## Phase 5: Compliance and Enterprise Controls

- [ ] Add audit logs for auth, report access, deletes, and admin actions.
- [ ] Add data retention policy and configurable purge windows.
- [ ] Add SSO (SAML/OIDC) and SCIM roadmap.
- [ ] Add encryption-at-rest strategy for report artifacts.

Definition of done:

- Security and compliance posture supports enterprise procurement.

## Suggested Delivery Cadence

- Sprint 1: Phase 1 + start Phase 2
- Sprint 2: finish Phase 2 + Phase 3
- Sprint 3: Phase 4 + baseline enterprise controls from Phase 5

## ComplyAI Differentiator To Protect While Scaling

ComplyAI's strongest moat is semantic control-level mapping plus remediation output in one flow:

- Policy sentence understanding instead of pure keyword checklists.
- Gap severity (`Aligned`, `Weak`, `Missing`) and actionable rewrite suggestions.
- Directly consumable outputs (PDF, JSON, CSV, dashboard trends) for audit workflows.

As SaaS features are added, preserve this by treating recommendation quality and explainability as first-class product metrics.
