# Security Policy

## Supported Versions

This is an actively developed portfolio project. Only the latest commit on `main` is supported; no older releases receive security fixes.

## Known, Documented Limitations (not vulnerabilities to report)

The following are intentional, documented scope decisions, not oversights:
- Authentication and role-based access control are implemented. Read APIs require an authenticated viewer, operator, or admin; operational writes require operator or admin access; structural writes require admin access.
- JWTs are signed with a required server-managed secret of at least 32 characters. Production deployments still need an external secret manager, key rotation, refresh-token/session revocation, and rate limiting.
- Kafka/Redpanda is configured for local development without TLS, SASL, or ACLs. A production broker must enable transport encryption, authenticated clients, and topic-level authorization.
- CORS origins are controlled via application settings (`app/core/config.py`) and should be restricted to trusted origins in any non-local environment.
- Seed data (`backend/scripts/seed.py`) is 100% synthetic and fictional; it is not representative of real users or robots.

## Reporting a Vulnerability

If you find a security issue that is not one of the documented limitations above (for example: SQL injection, a dependency CVE, a migration that could corrupt data, or a way to bypass validation), please do not open a public issue. Instead email sravanikamjula@gmail.com with:
- A description of the issue and its potential impact
- Steps to reproduce
- The affected file(s)/endpoint(s)

You should expect an acknowledgment within 5 business days.

## Disclosure

Once a reported issue is fixed, a summary will be added to CHANGELOG.md and the reporter credited unless anonymity is requested.

## Automated Security Gates

Pull requests and `main` are checked with Python and production JavaScript
dependency audits, CodeQL analysis for Python and JavaScript/TypeScript, and
Trivy scans of both production container images. Fixable high or critical
container findings fail the workflow. Dependabot checks Python, npm, GitHub
Actions, and Docker dependencies weekly. A green security workflow is evidence
that these configured checks passed at that commit; it is not a guarantee that
the software contains no vulnerabilities.
