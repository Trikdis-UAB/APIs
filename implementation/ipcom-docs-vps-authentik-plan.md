# Implementation Plan: Private Partner Docs on VPS (Caddy + Authentik)

## Summary
Move IPcom API documentation from public GitHub Pages to a private VPS-hosted docs portal with identity-based access.
Keep source in a private GitHub repo, keep GitHub Actions for build/deploy, and enforce per-user partner access via Authentik and Caddy `forward_auth`.

## Scope
- In scope: hosting, identity access control, CI/CD deploy, partner onboarding, logging, backup, rollout.
- Out of scope: changes to IPcom receiver API behavior, VPN rollout, custom auth app development.

## Important Interface Changes
- Public docs URL behavior changes from open access to authenticated access.
- New public-facing interfaces:
  - `https://api.docs.trikdis.com` (docs, auth-required)
  - `https://auth.trikdis.com` (identity provider + admin portal)
- No backend API contract changes for `/api/*` on IPcom receivers.
- New operational interfaces:
  - Admin user/group management in Authentik.
  - CI deploy pipeline from GitHub Actions to VPS.

## Target Architecture
- Private GitHub repository for docs source.
- GitHub Actions builds static docs artifact.
- VPS runs:
  - Caddy (TLS termination + reverse proxy + forward auth).
  - Authentik server + worker + PostgreSQL + Redis.
  - Authentik Proxy Outpost for Caddy integration.
- Static docs served from VPS path, example `/srv/ipcom-docs/current`.
- DNS:
  - `api.docs.trikdis.com` -> VPS.
  - `auth.trikdis.com` -> VPS.

## Required DNS and Platform Settings
### DNS Records (at current DNS provider)
| Host | Type | Value | TTL |
|---|---|---|---|
| `api.docs.trikdis.com` | `A` | `<VPS_PUBLIC_IP>` | `300` |
| `auth.trikdis.com` | `A` | `<VPS_PUBLIC_IP>` | `300` |

### Server and App Settings
- Firewall: allow inbound `80/443`; restrict inbound `22` to admin IPs where possible.
- Caddy TLS: automatic certificate issuance for `api.docs.trikdis.com` and `auth.trikdis.com`.
- Authentik external URL/redirect configuration must match the final hostnames.
- SMTP must be configured and tested for invites, password reset, and admin notifications.
- GitHub Actions repository secrets must be configured before first deploy.

### Optional Email Deliverability Hardening
- If Authentik sends mail from your domain, add SPF/DKIM/DMARC records for reliable delivery.

## Access Model
### Groups
| Group | Access |
|---|---|
| `ipcom-docs-admins` | Authentik admin + docs access |
| `ipcom-docs-partners` | Docs access |
| `ipcom-docs-pending` | Authenticated, no docs access |

### Policies
| Policy | Rule |
|---|---|
| Docs allow policy | user in `ipcom-docs-partners` or `ipcom-docs-admins` |
| Admin policy | user in `ipcom-docs-admins` |
| Default deny | everyone else denied |

## Implementation Phases

### 1. Infrastructure Prep
- Provision VPS with static public IP, firewall, and OS hardening.
- Open only `80/443`; block everything else externally.
- Restrict SSH access (`22`) to admin source IPs and disable password SSH login.
- Install Docker + Docker Compose plugin.
- Create directories:
  - `/opt/ipcom-auth/`
  - `/srv/ipcom-docs/releases/`
  - `/srv/ipcom-docs/current` (symlink target)
  - `/var/backups/ipcom-auth/`
- Create service account for deployments with restricted SSH key access.

### 2. Authentik Stack Deployment
- Deploy Authentik, PostgreSQL, Redis, and Outpost using Docker Compose in `/opt/ipcom-auth/`.
- Configure SMTP for password reset, invitations, and admin notifications.
- Set Authentik external URL values and trusted redirect URIs for both hostnames.
- Configure Authentik brand and login page text.
- Create groups listed in access model.
- Create application/provider for docs and connect Outpost.
- Create docs authorization policy (group-based allow).
- Configure session timeout:
  - Partners: 8 hours.
  - Admins: 4 hours.
- Enforce MFA for `ipcom-docs-admins`.

### 3. Caddy Setup
- Configure `Caddyfile` for both hostnames.
- Route `api.docs.trikdis.com` through `forward_auth` to Authentik Outpost.
- Serve static docs from `/srv/ipcom-docs/current`.
- Route `auth.trikdis.com` to Authentik server.
- Enable HTTPS with automatic certificates.
- Add security headers and compression.

### 4. Docs Build/Deploy Pipeline
- Keep docs in private GitHub repo.
- Add GitHub Actions workflow:
  - Trigger on merge to `main`.
  - Build static docs.
  - Run docs build validation command.
  - Upload artifact.
  - Deploy via SSH/rsync to `/srv/ipcom-docs/releases/<timestamp>`.
  - Switch symlink `/srv/ipcom-docs/current` atomically.
  - Keep last 5 releases.
- Store deploy secrets in GitHub Actions:
  - `VPS_HOST`
  - `VPS_USER`
  - `VPS_SSH_KEY`
  - `VPS_SSH_PORT`
- Add rollback job: set symlink to previous release.

### 5. Partner Provisioning and Access Operations
- Start with invite-only onboarding.
- Admin flow:
  - Invite user.
  - User sets password.
  - Admin assigns `ipcom-docs-partners`.
- Revoke flow:
  - Remove from group or disable account.
- Optional phase-2 self-registration:
  - Enable enrollment flow.
  - Auto-place new accounts in `ipcom-docs-pending`.
  - Email notification to admins on new signup.
  - Manual approval moves user to `ipcom-docs-partners`.

### 6. Security Hardening
- Disable public directory indexing for docs.
- Disable anonymous access entirely.
- Set brute-force protections and lockout thresholds in Authentik.
- Enable structured logs for Caddy and Authentik.
- Add daily PostgreSQL backup + weekly restore test.
- Add monthly access review for partner accounts.
- Keep docs sanitization backlog and remove unnecessary high-risk operational examples over time.

### 7. Cutover and Communication
- Soft launch with internal users first.
- Validate partner login with 2 pilot partners.
- Send partner notice with new access process and support contact.
- Keep legacy public docs available for 7 days with deprecation banner.
- Final cutover: redirect legacy docs URL to authenticated docs landing page.

## Test Cases and Scenarios
1. Anonymous user requests `api.docs.trikdis.com` and is redirected to Authentik login.
2. Valid partner account logs in and can access docs.
3. User in `ipcom-docs-pending` logs in and gets access denied to docs.
4. Revoked user loses access immediately.
5. Admin account requires MFA at login.
6. Session expiry forces re-authentication at configured TTL.
7. GitHub Actions deployment publishes new docs without downtime.
8. Rollback job restores previous docs release successfully.
9. SMTP notifications send invitation and reset emails successfully.
10. Backup restore drill successfully recovers Authentik database.

## Acceptance Criteria
- Docs are not publicly viewable without authentication.
- Partner access is managed per user with group-based authorization.
- Deployments are automated from private repo via GitHub Actions.
- Revocation is effective without server restarts.
- MFA is enforced for admins.
- Backup and rollback procedures are documented and tested.

## Rollout Timeline
### Risk-Managed Timeline (3 weeks)
- Week 1: VPS prep, Authentik + Caddy setup, internal auth testing.
- Week 2: CI/CD deploy pipeline, pilot partner onboarding, rollback test.
- Week 3: partner migration communication, phased cutover, legacy URL deprecation.

### Why 3 weeks if setup is mostly boilerplate
- The technical install itself is fast; most time is allocated to low-risk rollout tasks.
- The buffer covers partner coordination, communication lead time, pilot validation, and rollback rehearsal.
- This reduces outage and access-lockout risk during migration.

### Fast-Track Timeline (1-3 days, higher rollout risk)
- Day 1: Deploy Authentik + Caddy, apply invite-only policy, run internal auth tests, validate with one pilot partner.
- Day 2: Finalize CI/CD deployment job, execute rollback test, publish onboarding instructions, go live.
- Day 3 (optional): Post-go-live hardening (backup restore drill, log alert tuning, documentation cleanup).

## Assumptions and Defaults
- Current decision is VPS-hosted docs, not Cloudflare-first.
- GitHub account remains Free; repo becomes private.
- Domain and DNS changes for `api.docs.trikdis.com` and `auth.trikdis.com` are approved.
- Invite-only onboarding is default at launch.
- No custom application code is required for phase 1.
- Optional Cloudflare fronting is deferred and treated as future enhancement.
