# Contributing to Veritas

Thank you for your interest in contributing! This document covers the development workflow, code standards, and how to submit a pull request.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Branch Naming](#branch-naming)
- [Commit Messages](#commit-messages)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Code Style](#code-style)
- [Running Tests](#running-tests)
- [Reporting Issues](#reporting-issues)

---

## Getting Started

1. **Fork** the repository and clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/veritas.git
   cd veritas
   ```

2. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/veritas.git
   ```

3. Follow the [Local Development](README.md#option-b--local-development-manual) setup in the README.

---

## Development Setup

See [README.md → Option B](README.md#option-b--local-development-manual) for the full step-by-step local setup guide.

Quick summary:
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env          # Fill in SERPER_API_KEY
```

---

## Branch Naming

Use the following pattern: `type/short-description`

| Prefix | Use for |
|---|---|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `chore/` | Build, CI, dependency updates |
| `docs/` | Documentation only |
| `refactor/` | Refactors with no functional change |
| `test/` | Adding or fixing tests |

Examples:
- `feat/add-pdf-preview`
- `fix/celery-connection-retry`
- `docs/update-deployment-guide`

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(optional scope): <short summary>

[optional body]
[optional footer]
```

Examples:
```
feat(api): add /api/verify/text endpoint
fix(worker): handle empty article body gracefully
docs: update deployment guide for PostgreSQL
chore(deps): upgrade FastAPI to 0.115
```

---

## Submitting a Pull Request

1. Sync with upstream before starting:
   ```bash
   git fetch upstream && git rebase upstream/main
   ```

2. Create a new branch from `main`:
   ```bash
   git checkout -b feat/your-feature
   ```

3. Make your changes, write tests, and ensure all tests pass:
   ```bash
   python -m pytest tests/test_worker.py tests/test_verifier.py -v
   ```

4. Push and open a PR against `main`:
   ```bash
   git push origin feat/your-feature
   ```

5. Fill in the PR template completely. Link any related issues with `Closes #NNN`.

6. A maintainer will review your PR. Please address feedback promptly.

---

## Code Style

### Python (backend)

- Follow **PEP 8**
- Max line length: **100 characters**
- Use docstrings for all public functions and modules
- Type annotations are encouraged for new code

### JavaScript / JSX (frontend)

- Use **ES modules** (`import`/`export`)
- Prefer functional components and React hooks
- Keep components focused — split large components into smaller ones

---

## Running Tests

```bash
# Unit tests (no Redis or Celery needed)
python -m pytest tests/test_worker.py tests/test_verifier.py -v

# Integration tests (requires running API + Redis + Celery)
python -m pytest tests/test_api.py -v -s

# All tests
python -m pytest --tb=short -q
```

---

## Reporting Issues

Use the [GitHub Issues](../../issues) tracker. Please search for existing issues before opening a new one.

For **security vulnerabilities**, do **not** open a public issue — see [SECURITY.md](SECURITY.md) instead.
