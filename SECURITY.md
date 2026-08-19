# Security Policy

## Supported Versions

This is an actively developed portfolio project. Only the latest commit on `main` is supported; no older releases receive security fixes.

## Known, Documented Limitations (not vulnerabilities to report)

The following are intentional, in-progress scope decisions, not oversights:
- Authentication is implemented as a Phase 6 foundation only; RBAC enforcement remains out of scope for this slice. All existing routes remain open until route-level authorization is added in a later phase.
- JWTs are signed with a server-managed secret and should never be used in production without a non-default secret configured through environment variables.
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
