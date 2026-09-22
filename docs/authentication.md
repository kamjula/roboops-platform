# Authentication and session lifecycle

RoboOps uses short-lived signed JWT access tokens for human users. Login verifies
an Argon2 password hash, creates an `auth_sessions` row, and embeds that session
UUID in the token's `jti` claim. Each protected request validates both the JWT
signature and the corresponding unexpired, non-revoked database session before
loading the active user and applying viewer/operator/admin authorization.

`POST /api/v1/auth/logout` revokes only the session represented by the submitted
bearer token. Reusing that token then returns `401`; another active session for
the same user remains valid. The React client calls this endpoint before removing
its session-storage token. It still clears local state if the network request
fails so a user is not left signed in on a shared browser.

Expired session rows for a user are pruned when that user logs in again. Deleting
a user cascades to their session rows.

This implementation does not claim refresh-token rotation, global logout across
all devices, managed signing-key rotation, or external identity-provider/SSO
support. Those remain separate production-hardening concerns.
