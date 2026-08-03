# Security Policy

## Supported versions

Security fixes are applied to the latest code on the `main` branch and to active release-candidate branches. Older commits and unofficial distributions are not supported.

## Reporting a vulnerability

Do not report vulnerabilities in a public issue, discussion, pull request, or social-media post.

Use GitHub private vulnerability reporting when it is available:

1. Open the repository's **Security** tab.
2. Select **Advisories**.
3. Select **Report a vulnerability**.

If private reporting is unavailable, open a public issue containing no sensitive technical details and ask the maintainer to establish a private channel.

Include the affected command or file, impact, reproducible steps, and sanitized logs. Remove tokens, cookies, session files, and personal library data.

## Sensitive files

`tidal-session-oauth.json` may provide access to a TIDAL account. Backups, reports, and operation logs may disclose private library metadata.

- Never commit session files, access tokens, cookies, credentials, or personal backups.
- Revoke or refresh exposed credentials immediately.
- Store generated files with access restricted to the account owner.
- Remove sensitive data from logs, screenshots, fixtures, and reports.

## Legacy pickle backups

Python pickle data can execute code while loading. tidal-utils uses a restricted compatibility loader that blocks arbitrary global callables, but this is defense in depth rather than a guarantee that arbitrary pickle data is safe.

Only migrate or inspect legacy `.pkl` files that you created yourself or received from a fully trusted source. Prefer the JSON backup format for all new backups.

## Scope

Security reports may include credential exposure, unsafe backup processing, unintended destructive operations, path or symlink attacks, injection through remote metadata, dependency vulnerabilities, workflow supply-chain risks, or disclosure of private library information.

General bugs and matching-quality issues without a security impact should be filed as normal issues.

## Coordinated disclosure

Avoid privacy violations, service disruption, data destruction, and access to accounts or data you do not own. Allow a reasonable remediation period before public disclosure.
