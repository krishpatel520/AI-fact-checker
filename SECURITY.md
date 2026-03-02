# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| Latest (`main`) | ✅ |

---

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability, please send a description to the project maintainer via one of the following methods:

- **GitHub Private Vulnerability Reporting**: Use the [Security tab → Report a vulnerability](../../security/advisories/new) button on this repository.
- **Email**: Contact the maintainer directly (check the repository profile for contact info).

Please include as much of the following information as possible to help understand and resolve the issue quickly:

- Type of issue (e.g. API key exposure, SSRF, injection, CORS misconfiguration)
- Full path of the affected source file(s)
- Location of the vulnerable code (tag, branch, commit, or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue and how an attacker might exploit it

---

## What to Expect

- You will receive an acknowledgement within **48 hours**.
- We will confirm the vulnerability and determine its severity.
- We will work on a fix and release a patch as quickly as possible depending on severity.
- We will publicly disclose the vulnerability after a fix is released, crediting the reporter (unless you prefer to remain anonymous).

---

## Scope

The following are **in scope**:

- The FastAPI backend (`backend/`)
- CORS and authentication mechanisms
- Secret/key exposure or mishandling
- Dependency vulnerabilities with a known public CVE

The following are **out of scope**:

- Vulnerabilities in third-party services (Serper.dev, ScrapingBee, Redis)
- Issues affecting only local development environments
- Social engineering attacks

---

## Preferred Language

Please report in **English**.
