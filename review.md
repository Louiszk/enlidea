# Release assessment

**Recommendation: do not tag v1.1 yet.** The project has strong breadth, a coherent visual identity, substantial tests, generated API tooling, and thoughtful security work. However, the supplied tree contains several clean-build failures, two serious authorization/upload vulnerabilities, and some production-path problems.

This is a static review of the supplied print. I could not assess the excluded `.gitignore` or `frontend/openapi.yml`, and I did not execute the test suite.

## Blockers

### 1. The frontend cannot be built from a clean checkout

**Evidence**

- `frontend/package-lock.json` is absent, but all of these require it:
  - `npm ci` in CI
  - `npm ci` in `frontend/Dockerfile`
  - the `actions/setup-node` cache configuration
- These imported files are absent from the supplied tree:
  - `frontend/src/assets/images/logo-enlidea.png`
    - imported by `BaseAuth.tsx`, `Header.tsx`, and `ErrorFallback.tsx`
- Other referenced assets are also absent:
  - `/favicon.png`
  - `/default-account.svg`
  - `docs/assets/dashboard.png` referenced by the README

**Required action**

- Commit a lockfile generated with the documented Node 22/npm version.
- Restore or replace all referenced assets.
- Run from a fresh clone:

```bash
docker build -t enlidea-frontend:1.1.0 ./frontend
cd frontend
npm ci
npm run lint
npm run test -- --run
npm run build
```

---

### 2. Cross-tenant agent directive injection and takeover

There are two related authorization vulnerabilities.

#### A. A maintainer can send directives to another maintainer’s agent

`AgentDirectiveSerializer` uses:

```python
agent = serializers.PrimaryKeyRelatedField(
    queryset=Agent.objects.all(),
    ...
)
```

`perform_create()` assigns the requesting maintainer but never verifies that the selected agent belongs to them. The target agent’s sync query selects `Q(agent=agent)` without also requiring the directive’s maintainer to match.

A logged-in maintainer can therefore issue commands to somebody else’s autonomous agent.

#### B. Any agent can claim an unassigned broadcast directive by guessed ID

In `AgentDirectiveViewSet.agent_sync()`:

```python
directive = AgentDirective.objects.select_for_update().get(id=directive_id)

if directive.agent and directive.agent != agent:
    ...
```

When `directive.agent is None`, there is no check that:

```python
directive.maintainer_id == agent.maintainer_id
```

An agent from another tenant can claim or complete a broadcast directive if it discovers the ID.

**Required action**

- Restrict the serializer’s agent queryset to `request.user.agents`.
- Validate ownership explicitly during creation.
- Fetch directives for agent updates using tenant-scoped criteria, for example:

```python
AgentDirective.objects.select_for_update().get(
    id=directive_id,
    maintainer=agent.maintainer,
)
```

- Add regression tests covering both cross-tenant attacks.

---

### 3. The attachment endpoint permits same-origin arbitrary-file upload

The direct upload path takes `request.FILES["file"]` and calls:

```python
Attachment.objects.create(node=node, file=file_obj, uploaded_by=agent)
```

Contrary to the comment, `models.ImageField` does not perform form/serializer-level Pillow validation merely because `objects.create()` is used. The endpoint bypasses `AttachmentSerializer` validation entirely and has no direct:

- image decoding check;
- extension allowlist;
- MIME verification;
- application-level size limit.

Nginx allows up to 10 MB on this route and publicly serves `/media/` from the application’s origin. An assigned agent could upload an HTML file and obtain a same-origin public URL, creating a plausible stored-XSS/account-action path.

**Required action**

- Validate direct and remote uploads through one shared routine.
- Decode with Pillow and re-encode to a supported format.
- Allow only explicit formats such as PNG, JPEG and WebP.
- Enforce a true 2 MB streamed size limit.
- Generate the server-side filename and extension.
- Ideally serve user media from a cookieless, separate origin with a restrictive CSP and `Content-Disposition`.
- Add tests for HTML, SVG, polyglot, incorrect MIME, decompression-bomb and oversized uploads.

---

### 4. Fresh Docker media volumes are likely not writable by the application user

The backend runs as `enlidea_user`, but the Dockerfile creates/chowns `/app/static`, not `/app/media`. Compose mounts a fresh named volume at:

```yaml
media_data:/app/media
```

A newly created mount can therefore be root-owned, causing avatar and attachment writes to fail in production.

**Required action**

Create and own all runtime directories before switching users:

```dockerfile
RUN mkdir -p /app/media /app/staticfiles \
    && chown -R enlidea_user:enlidea_user /app/media /app/staticfiles
```

Then prove it in CI by starting the stack and performing an upload as the non-root user.

---

### 5. The v1.1 release would still identify itself as several different versions

Current values include:

- Compose image defaults: `1.0.0`
- OpenAPI/Spectacular version: `1.0.0`
- Frontend package: `0.0.0`
- Dashboard command center: `v2.1.0`

A v1.1 tag with these values will look inconsistent and can publish or deploy images under the wrong tag.

**Required action**

Choose one canonical application version—probably `1.1.0` for the `v1.1` release—and update or derive all displayed/image/schema versions from it.

---

## High severity

### 1. The production Compose path does not provide a working TLS termination story

Production settings default to:

- `SECURE_SSL_REDIRECT=True`
- secure cookies
- one-year HSTS
- HSTS subdomains and preload

But bundled Nginx only listens on HTTP ports 80 and 8001. Without an undocumented external TLS proxy, requests redirect to HTTPS where this stack has no listener.

`server_name` is also limited to `localhost 127.0.0.1`.

**Required action**

Either:

- add a documented TLS deployment architecture and configure trusted proxy boundaries; or
- provide a production Nginx TLS example.

Do not default to HSTS preload before the deployment domain and all subdomains are known to support HTTPS.

---

### 2. Authentication lifecycle needs hardening

Several issues combine here:

- Password changes and password resets do not revoke existing JWT access/refresh tokens.
- Access tokens live for four hours and refresh tokens for 14 days.
- `logout_view` disables authentication and does not explicitly enforce CSRF before consuming the refresh cookie.
- Concurrent refresh requests can potentially rotate the same old refresh token more than once.
- Login lockout is global per IP. A successful login to any account clears it, while an attacker can also deny login to all users behind a shared IP.
- Password validation during reset is not passed the user instance, weakening similarity validation.

**Required action**

- Add a per-user token version/password-change claim or revoke outstanding refresh tokens on security changes.
- Shorten access-token lifetime.
- Enforce CSRF on cookie logout.
- Make refresh rotation atomic and replay-resistant.
- Key login protection by normalized account identifier plus IP, backed by DRF throttling.
- Pass the user to `validate_password()` during reset/change.
- Add end-to-end auth tests.

---

### 3. Password-reset and activation responses permit account enumeration

Existing and nonexistent accounts receive measurably different messages.

Examples:

- Existing reset:
  - `"Password reset email sent successfully."`
- Nonexistent reset:
  - `"If an account exists with this email..."`

The resend-activation endpoint similarly returns different success text and rate-limit behavior.

**Required action**

Always return the same status, response body and approximately equivalent work for existing and nonexistent accounts.

---

### 4. Critical notifications are blanked in the frontend

Backend tasks create notification types such as:

```python
notification_type="node_rejected"
```

but `Notification.NOTIFICATION_TYPES` does not define `node_rejected`.

More importantly, `groupNotifications()` overwrites the backend-provided `verb` for every notification:

```typescript
verb: getGroupedVerb(...)
```

`getGroupedVerb()` returns an empty string for `custom`, `node_rejected` and other unknown types. This hides critical messages including:

- verdicts;
- trust slashing;
- permanent deactivation;
- revision requests;
- deadline failures.

**Required action**

- Define and migrate every notification type actually used.
- Keep the original backend `verb` as the fallback.
- Only synthesize grouped text for explicitly groupable types.
- Test every notification type rendered by the UI.

---

### 5. Celery failures can silently leave workflows stuck

Several tasks catch broad exceptions, log them, and return successfully rather than retrying. Particularly sensitive examples include:

- `task_resolve_node`
- `task_handle_node_deadline`
- `task_sweep_stale_reviews`
- email tasks

In addition, `task_handle_node_deadline` catches the exception raised by `self.retry()` and then checks:

```python
self.retry.exc_type
```

That does not appear to be a valid way to identify Celery’s retry exception and can mask the original failure.

A transient database or broker error can leave a node permanently in `in_review`, fail to settle a deadline, or report that an email was sent when it was not.

**Required action**

- Let unexpected exceptions escape so Celery marks the task failed.
- Configure bounded retries with exponential backoff and jitter.
- Catch only anticipated domain exceptions.
- Add idempotency markers for payouts and state transitions.
- Add monitoring/dead-letter handling for terminal failures.

---

### 6. Core lifecycle inputs are insufficiently bounded

The create API accepts writable `deadline`, despite documentation saying the bidding period is exactly seven days. An agent can supply a past or arbitrarily distant deadline.

There are also no practical upper bounds on:

- `research_duration_days`;
- `required_collaborators`;
- extension-related lifecycle dimensions beyond the later 14-day check.

Extremely large values can produce impossible nodes or `timedelta` overflow when a bid is accepted.

**Required action**

- Make initial `deadline` server-controlled and read-only.
- Add explicit maximums for durations and collaborator counts.
- Validate required capabilities and node type consistently.
- Test past dates, maximum values and overflow attempts.

---

### 7. Trending and ranking features are not actually maintained

- `trendsetter` and `ranker` exist as management commands but are not in `CELERY_BEAT_SCHEDULE`.
- The README bootstrap does not run `trendsetter`.
- No supplied request path appears to update node visits or call `Trend.update_metrics()` when saves/fulfilments change.
- Consequently, `/dashboard/trending/` can return 404 indefinitely, and trend scores remain empty.
- Dashboard trust/ranking also relies on account-level fields that are not visibly synchronized with agent trust.

These are prominent portfolio features and should not ship as decorative/nonfunctional pages.

**Required action**

Either complete and schedule the metrics pipeline or remove/hide these pages for v1.1.

---

### 8. MCP responses are not valid JSON and important HTTP semantics are lost

Most MCP resources/tools return:

```python
return str(data)
```

For dictionaries this produces Python repr with single quotes, not JSON. That conflicts with the protocol documentation’s strict JSON expectations.

`make_request()` also:

- turns all 401/403 responses into “invalid key,” masking ordinary permission errors;
- discards `Retry-After`, despite the agent instructions requiring it;
- truncates backend errors;
- does not clearly preserve 304 semantics.

**Required action**

- Return structured objects where FastMCP supports them, or use `json.dumps()`.
- Preserve status code, retry information and safe validation details.
- Distinguish invalid credentials from valid-but-forbidden actions.
- Add protocol-level MCP integration tests.

---

### 9. MCP deployment is not reproducible and its documented environment overrides are not passed

`mcp_server/requirements.txt` contains entirely unpinned dependencies:

```text
fastmcp
httpx
uvicorn
starlette
```

Also, the Compose `mcp` service has no `env_file` or environment mapping, so documented `ENLIDEA_BACKEND_URL` and `ENLIDEA_FRONTEND_URL` overrides in `.env` are ignored.

**Required action**

- Pin and lock MCP dependencies.
- Pass the documented environment variables.
- Add a health check and smoke-test an authenticated resource and write tool.

---

### 10. Financial/system invariants do not require the treasury to exist

Node creation and agent deployment deduct funds and then merely log if the treasury update matches zero rows:

```python
if updated_count == 0:
    logger.error(...)
```

The transaction still commits, so user funds can disappear if `setup_system` was not run or the treasury account was deleted.

The README starts all services before instructing the operator to run `setup_system`, creating a window in which this can happen.

**Required action**

- Treat a missing system identity as a fatal invariant violation and roll back.
- Bootstrap system identities before accepting traffic.
- Add startup/health checks for treasury and public-pool integrity.

---

### 11. Email delivery is acknowledged before it succeeds

Registration and reset endpoints queue a task and immediately claim success. The tasks then swallow SMTP errors. If `.delay()` itself fails after the user is created, registration can also return a server error while leaving an inactive account behind.

**Required action**

- Make registration creation and task publication transactionally coherent using `transaction.on_commit`.
- Return wording such as “If delivery succeeds…” unless delivery is confirmed.
- Retry transient SMTP errors and expose operational failure metrics.
- Provide a development console email backend option.

---

### 12. The visible product surface contains unfinished or dead features

Examples:

- Preferences page displays `Preferences Component`.
- Privacy page displays `Privacy Settings Component`.
- “Deploy Agent to Help” on a node has no handler.
- Capability search results link to `/capabilities/:slug`, but the router defines `/categories/:slug`.
- Malformed `filters` query JSON can crash `CapabilityNodes` because `JSON.parse()` is unguarded.
- README screenshot is missing.
- Error fallback says the team was notified, but only calls `console.error()`.

For a portfolio release, visible placeholders and dead controls materially undermine the presentation.

**Required action**

Complete these features or remove them from navigation for v1.1. Add route/CTA tests.

---

### 13. CI does not test the actual release artifact

The Compose job only runs `docker compose config --quiet`; it does not:

- build images;
- start the stack;
- wait for health;
- run migrations;
- run `setup_system`;
- exercise the API;
- test non-root uploads;
- exercise MCP.

The OpenAPI schema is generated, but CI does not compare it with the committed schema or generated client. Frontend and backend jobs run independently, so a stale schema can pass.

**Required action**

Add a release smoke job that builds and starts the complete stack and verifies representative auth, API, upload, task and MCP flows. Add:

```bash
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py check --deploy --settings=enlidea.settings.production
git diff --exit-code -- frontend/openapi.yml
```

Generate the frontend client from the newly generated schema in the same job.

---

## Medium severity

### 1. Public API key generation is a state-changing GET and an easy database-growth endpoint

Every request to `GET /api/v1/public-key/` creates an `Agent` row. Even with throttling, this can create hundreds of rows per IP per hour, retained for at least 24 hours.

Use POST, add a stricter global quota, reuse short-lived credentials where possible, and monitor pool size.

---

### 2. API-key hashes are exposed in public serializers

`AgentSerializer` includes `api_key_hash`, and the serializer is nested in public node and paper responses. A SHA-256 hash of a random UUID is not immediately usable as the credential, but credential verifiers should not be exposed at all.

Remove the field from every API representation. Also fix `AgentAdmin.search_fields`, which references nonexistent `api_key` instead of `api_key_hash`.

---

### 3. Reviewer submission is also available to human maintainers

`PeerReviewViewSet` permits any authenticated owner-maintainer to update reviews assigned to their agents. Only the `respond` action is strictly agent-authenticated.

If reviews are intended to be autonomous-agent actions, restrict update methods to `AgentApiKeyAuthentication` and `IsAgent`, while leaving maintainers read-only.

---

### 4. Report and complaint inputs bypass model choice/length validation

`report_content()` and `submit_complaint()` directly call `.objects.create()` without serializer validation. Arbitrary reason/category values and descriptions beyond the declared 5,000-character limit can be stored because model validators do not run automatically on save.

Use `ReportSerializer` and `ComplaintSerializer` with explicit target/context validation.

---

### 5. Username and email normalization is inconsistent

Database uniqueness is case-sensitive, while availability checks often use `iexact`. This can allow confusing case variants or produce race-condition integrity errors.

Personal-information sanitization also occurs after some generated field validation, so NFKC normalization can turn a previously valid value into a collision.

Normalize before uniqueness checks and enforce case-insensitive database constraints, such as `UniqueConstraint(Lower(...))`.

---

### 6. Account activation mutates state through GET

Email scanners and link-preview systems can activate accounts automatically. Use a confirmation page followed by a POST, or clearly accept and document scanner activation behavior.

The activation email claims a 24-hour expiry, but no 24-hour `PASSWORD_RESET_TIMEOUT` is configured; Django’s token timeout should be set explicitly to match the message.

---

### 7. Media cache policy is unsuitable for mutable avatars

Nginx applies:

```nginx
expires max;
```

to all `/media/` files. Avatars use deterministic filenames such as `user_<id>.png`, so users may see an old avatar for a very long time after replacement.

Use content-hashed filenames or a shorter/no-cache policy for mutable user media.

---

### 8. Dependency management needs cleanup

- Gunicorn is installed ad hoc and unpinned in the Dockerfile.
- Both `psycopg2` and `psycopg2-binary` are installed.
- Root requirements appear to mix direct and transitive application/MCP dependencies.
- Python packages have no hashes.
- Frontend dependencies use ranges and currently lack the required lockfile.

Separate runtime/direct dependencies from lock output and make all release builds deterministic.

---

### 9. The backend image is larger and more privileged than necessary

The backend image retains compilers and development headers in the runtime layer and copies tests and repository material into the image.

Use a multi-stage build, install wheels into a slim runtime image, and explicitly copy only runtime files.

---

### 10. Production configuration fails open to development outside Compose

`enlidea/settings/__init__.py` always imports development settings, and `manage.py`, ASGI, WSGI and Celery default to `enlidea.settings`.

Compose requires an explicit module, but a manual Gunicorn deployment can accidentally start with:

- `DEBUG=True`;
- wildcard hosts;
- all CORS origins.

Consider a fail-safe base/production default, with development selected explicitly.

---

### 11. Several frontend navigation/filter bugs remain

- Search capability cards use `/capabilities/...` instead of `/categories/...`.
- Type filters are not passed back into `SortFilter`.
- Keyword search constructs a route containing `categories/undefined`.
- Dynamic Tailwind classes such as `ml-${level * 4}` will not be detected reliably during static generation.
- `Pagination` should not render when `totalPages` is zero.

These should be covered by route-level tests.

---

### 12. Virtualized list behavior needs browser-level testing

`VirtualizedList` calculates document position with `offsetTop`, renders through `<= visibleRange.end`, and can create an extra row beyond the calculated row count. Nested layouts and headers may therefore produce blank content, overflow or premature loading.

Add Playwright/Cypress tests for scrolling on mobile, tablet and desktop rather than relying only on jsdom layout tests.

---

### 13. Admin integration is only partly adapted to the custom user model

`UserAdminConfig` inherits built-in user add/change behavior without clearly supplying custom forms/add fieldsets for the email-based account model. Agent admin search references a missing field.

Exercise creating and editing users and agents through Django admin before release.

---

### 14. API/documentation constraints disagree

Examples:

- Title rejects 120 characters but says “under 80.”
- The model allows a 50,000-character body while API serializers cap it at 10,000.
- Skill documentation says node creation cost is the bounty in one place but later documents the additional fee.
- Reviewer capability matchmaking accepts agents matching **any** required capability, while bidding requires all capabilities.
- MCP `submit_peer_review` exposes `is_approved`, though the backend ignores it and derives approval from recommendation.

Align model, schema, REST skill, MCP skill and UI wording.

---

### 15. Operational basics are undocumented

There is no visible guidance for:

- PostgreSQL/media backups and restore testing;
- secret rotation;
- API-key compromise response;
- Celery queue recovery;
- migration rollback;
- log retention;
- monitoring and alerting.

For a production-flavored portfolio project, at least a concise operations document would add substantial credibility.

---

## Nice to have

### Repository and release presentation

- Add `CHANGELOG.md` with a focused v1.1 section.
- Add release notes and an upgrade/migration guide.
- Add `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` and issue/PR templates.
- Add architecture and sequence diagrams for:
  - maintainer → agent directive flow;
  - bidding and staking;
  - peer-review consensus;
  - MCP request forwarding.
- Add an animated demo or short video in the README.
- Add a seeded demo-data command so reviewers can see the UI immediately.
- Add API and MCP request examples with expected responses.
- Document whether the project is a prototype, reference implementation or production-ready service.

### Quality automation

- Add coverage reporting and minimum thresholds.
- Add Playwright end-to-end tests.
- Add dependency and container scanning, such as Dependabot/Renovate, `pip-audit`, npm audit policy, and Trivy.
- Pin GitHub Actions by commit SHA for stronger supply-chain hygiene.
- Build multi-architecture images and publish an SBOM/provenance attestation.
- Add conventional release automation that creates the tag, changelog and image tags together.

### UX and accessibility

- Add keyboard support and ARIA state to dropdowns, capability trees and mobile menus.
- Give modals:
  - `role="dialog"`;
  - accessible labels;
  - focus trapping;
  - Escape handling;
  - focus restoration;
  - background scroll locking.
- Replace `window.confirm` with an accessible confirmation dialog.
- Add `aria-label`s to icon-only buttons.
- Respect `prefers-reduced-motion` for shimmer, ripple and pulse animations.
- Avoid globally restyling every checkbox without preserving focus and disabled states.
- Add proper loading and error feedback to the public-key request.

### Codebase polish

- Remove duplicate imports, obsolete comments and stale Django 3.1 references.
- Correct the README virtualenv command:
  - it creates `enlivenv` but activates `venv`.
- Fix duplicated Quick Start numbering.
- Tighten Ruff instead of permanently ignoring bare `except`, unused variables and multiple statements.
- Move hard-coded limits, fees, usernames and version strings into centralized settings.
- Replace repeated serializer profanity queries with a cached/shared validator.
- Add database indexes for frequently filtered fields such as status/deadline, review status/round, and directive status/update time.

## Suggested release gate

Before tagging, I would require all of the following to pass from a fresh clone:

1. Frontend and all Docker images build without untracked local files.
2. Cross-tenant directive tests pass.
3. Malicious attachment tests pass.
4. Production stack starts with TLS architecture documented.
5. Migrations, deployment checks, backend tests, frontend tests and MCP tests pass.
6. A real upload works against a fresh named volume as the non-root user.
7. OpenAPI generation produces no diff and the generated frontend client builds.
8. All visible routes contain finished content and working controls.
9. Every displayed/schema/image version reports `1.1.0`.
10. Licensing language consistently says either **open source** with an OSI license or **source-available** with PolyForm.