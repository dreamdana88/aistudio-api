# Security Policy

## Sensitive data

Never open an issue or commit files containing:

- Google cookies, `auth.json`, or browser profiles
- `.env` files, API keys, proxy credentials, or access tokens
- Logs or screenshots that expose account details

The repository CI checks tracked files for common credentials and runtime data,
but automated scanning is not a substitute for reviewing changes before push.

If sensitive data is accidentally exposed:

1. Revoke or rotate it immediately.
2. Remove it from Git history rather than only deleting the latest copy.
3. Report the incident privately to the repository owner.

## Public deployments

Public deployments must use HTTPS and an `AISTUDIO_API_KEY` of at least 32
random characters. Do not expose the container port directly to the Internet;
bind it to `127.0.0.1` and place it behind a trusted reverse proxy.
