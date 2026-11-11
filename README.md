# Robots.txt & AEO Auditor

![Robots.txt Auditor Hero Banner](assets/hero-banner.svg)

**Robots.txt & AEO Auditor** (`robots-txt-auditor`) is a zero-dependency RFC 9309 `robots.txt` parser, AI crawler policy simulator, rule-drift analyzer, and local HTTP workstation (`127.0.0.1:8086`). Both the standalone browser client (`public/`) and the Python 3.9+ HTTP daemon (`server.py`) evaluate directive precedence without external runtime dependencies.

- **Zoth Studio v2 Dossier**: [https://zoth.nullai.tech/tools/robots-txt-auditor](https://zoth.nullai.tech/tools/robots-txt-auditor)
- **Repository**: [https://github.com/1nc0gn30/robots-txt-auditor](https://github.com/1nc0gn30/robots-txt-auditor)
- **Default Loopback Endpoint**: `http://127.0.0.1:8086`

---

## Overview

Modern web properties govern both search engine crawlers and AI answer engines (`GPTBot`, `OAI-SearchBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, `Applebot-Extended`, `CCBot`, `Bytespider`). `robots-txt-auditor` parses `robots.txt` files against RFC 9309 rules and evaluates crawler access deterministically:

- **RFC 9309 Directive Parser (`parse_robots_txt`)**: Groups `User-agent` blocks, evaluates `Allow`, `Disallow`, `Crawl-delay`, and `Sitemap` declarations, and detects root lockouts (`Disallow: /`), missing sitemap declarations, and excessive crawl delays.
- **AI Crawler Matrix**: Computes effective access (`ALLOWED` vs. `BLOCKED`), inherited wildcard (`*`) fallback vs. explicit bot overrides, and active `Disallow` patterns across major search and AI bots.
- **Curated Policy Presets (`PRESETS`)**: Built-in `open_sovereign` (full search + AI answer engine access), `selective_ai` (allow search/citation bots while blocking training scrapers), and `stealth_disallow` templates.
- **Dual Execution Modes**: Runs 100% client-side in `public/index.html` or via the local REST API and CLI (`server.py` / `bin/robots-txt-auditor`).

---

## Architecture

```text
robots.txt Input (File / Raw Text / Named Preset)
       │
       ▼
RFC 9309 Parser (server.py :: parse_robots_txt)
   ├── User-Agent Group Resolver (explicit bot rule vs '*' fallback)
   ├── AI Crawler Matrix (GPTBot, ClaudeBot, PerplexityBot, Googlebot, ...)
   ├── Sitemap & Crawl-Delay Hygiene Scorer (0–100 score, A+ to F grade)
   └── HTTP Workstation (127.0.0.1:8086) + CLI (bin/robots-txt-auditor)
```

---

## Quickstart

```bash
git clone https://github.com/1nc0gn30/robots-txt-auditor.git
cd robots-txt-auditor

# Start the HTTP workstation and REST API on 127.0.0.1:8086
python3 server.py --host 127.0.0.1 --port 8086
```

Open `http://127.0.0.1:8086` in your browser, or run via npm scripts:

```bash
npm run serve
```

---

## CLI & ZothOS v3.4.0 Integration

`bin/robots-txt-auditor` audits files, raw strings, or named presets directly (using the running `:8086` daemon when online or falling back to `parse_robots_txt` in-process):

```bash
# Check daemon health and JSON telemetry
./bin/robots-txt-auditor --status
./bin/robots-txt-auditor --json

# List curated RFC 9309 & AI crawler policy presets
./bin/robots-txt-auditor --presets

# Audit a named preset or local robots.txt file
./bin/robots-txt-auditor --preset open_sovereign
./bin/robots-txt-auditor --audit public/robots.txt --json

# Start the local daemon on 127.0.0.1:8086 if not already running
./bin/robots-txt-auditor --serve
```

---

## REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Web auditor workstation (`public/index.html`) |
| `GET` | `/health`, `/api/health` | Service health, version, uptime, and feature list |
| `GET` | `/api/presets` | Retrieve curated `robots.txt` policy templates |
| `POST` | `/api/parse`, `/api/audit` | Parse and score `{"content": "User-agent: *\nAllow: /\n..."}` |

Example `curl` audit:

```bash
curl -s -X POST http://127.0.0.1:8086/api/audit \
  -H "Content-Type: application/json" \
  -d '{"content": "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml"}'
```

---

## Testing & Verification

```bash
python3 -m pytest -q
./bin/robots-txt-auditor --help
./bin/robots-txt-auditor --preset selective_ai --json
```

---

## Support & License

100% free and open-source software under the MIT License.

- Optional support: [Buy Us a Coffee via Stripe](https://buy.stripe.com/3cIfZg27PdKo2D64Ocfw40X)
- Engineered by **1nc0gn30** (`@1nc0gn30`, [https://1nc0gn30.si](https://1nc0gn30.si)) • **NullAI** ([https://nullai.tech](https://nullai.tech))
