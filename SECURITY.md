# Security Policy

## Supported versions

Security fixes are applied to the latest code on the `main` branch. Older commits, forks, and unofficial distributions are not supported.

| Version | Supported |
| --- | --- |
| Latest `main` | Yes |
| Older versions | No |

## Reporting a vulnerability

Please do not report security vulnerabilities in a public issue, discussion, pull request, or social-media post.

Use GitHub's private vulnerability reporting feature for this repository when it is available:

1. Open the repository's **Security** tab.
2. Select **Advisories**.
3. Select **Report a vulnerability** or **New draft security advisory**.

If private vulnerability reporting is unavailable, open a public issue that contains no sensitive technical details and asks the maintainer to establish a private communication channel.

A useful report should include:

- a clear description of the vulnerability and its impact;
- the affected command, file, or version;
- reproducible steps or a minimal proof of concept;
- any relevant logs with tokens and personal data removed;
- suggested mitigations, when known.

You should receive an acknowledgement after the report is reviewed. Resolution time depends on severity, reproducibility, and maintainer availability. Please allow a reasonable remediation period before public disclosure.

## Sensitive files and credentials

This project can use a TIDAL session file such as `tidal-session-oauth.json`. Treat that file as a secret because it may provide access to a TIDAL account.

- Never commit session files, access tokens, cookies, credentials, or private library exports.
- Revoke or refresh exposed credentials immediately.
- Remove secrets and personal library data from logs, screenshots, bug reports, and test fixtures.
- Store backups and operation logs with permissions appropriate for personal account data.

## Legacy pickle backups

Python pickle files can execute code when loaded. Only migrate or inspect legacy `.pkl` backups that you created yourself or obtained from a source you fully trust.

The JSON backup format should be preferred for new backups because it is human-readable and does not execute Python objects while loading.

## Scope

Security reports may include, but are not limited to:

- credential or session-token exposure;
- unsafe loading of untrusted backup data;
- unintended destructive collection or playlist operations;
- command injection, path traversal, or arbitrary file access;
- dependency vulnerabilities with a practical impact on this project;
- disclosure of private TIDAL library metadata.

General bugs, feature requests, and matching-quality issues that do not have a security impact should be filed as normal GitHub issues.

## Coordinated disclosure

Please make a good-faith effort to avoid privacy violations, service disruption, data destruction, and access to accounts or data that you do not own. Do not publicly disclose an unresolved vulnerability before the maintainer has had a reasonable opportunity to investigate and release a fix.
