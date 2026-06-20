# Contributing

Create changes from the latest upstream branch and keep commits focused so each
change can be reviewed and reverted independently.

Before committing:

```bash
python .github/check_secrets.py
python -m pytest -q
```

Do not add `data/`, `.env`, `auth.json`, cookies, browser profiles, proxy
credentials, or personal account information. Use `.env.example` for safe
configuration examples.

By contributing, you agree that your contribution is licensed under the MIT
License and that upstream attribution in `NOTICE` will be preserved.
