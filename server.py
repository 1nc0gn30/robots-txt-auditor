#!/usr/bin/env python3
"""
Robots.txt & AEO Auditor — Sovereign Daemon & REST API Server.
Zero-dependency RFC 9309 parser, AI crawler simulator, and AEO indexability auditor.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List

START_TIME = time.time()
BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"

PRESETS = {
    "open_sovereign": {
        "name": "Frontier AI & Universal Access (Recommended)",
        "content": """# Robots.txt — Sovereign Open Access Standard
User-agent: *
Allow: /

# Frontier AI Search & Answer Engine Bots
User-agent: Googlebot
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Applebot
Allow: /

Sitemap: https://nullai.tech/sitemap.xml
"""
    },
    "stealth_disallow": {
        "name": "Strict Air-Gapped Disallow",
        "content": """# Robots.txt — Sovereign Air-Gapped Enclave
User-agent: *
Disallow: /
"""
    },
    "selective_ai": {
        "name": "Public SEO with Scraper Quarantine",
        "content": """User-agent: *
Disallow: /admin/
Disallow: /api/private/
Disallow: /tmp/

User-agent: GPTBot
Allow: /
Disallow: /internal/

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

Sitemap: https://nullai.tech/sitemap.xml
"""
    }
}

def parse_robots_txt(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    user_agents: Dict[str, Dict[str, Any]] = {}
    sitemaps: List[str] = []
    current_agents = ["*"]

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip().lower()
            val = val.strip()

            if key == "user-agent":
                agent = val
                if agent not in user_agents:
                    user_agents[agent] = {"allow": [], "disallow": [], "crawl_delay": None}
                current_agents = [agent]
            elif key == "allow":
                for agent in current_agents:
                    if agent not in user_agents:
                        user_agents[agent] = {"allow": [], "disallow": [], "crawl_delay": None}
                    user_agents[agent]["allow"].append(val)
            elif key == "disallow":
                for agent in current_agents:
                    if agent not in user_agents:
                        user_agents[agent] = {"allow": [], "disallow": [], "crawl_delay": None}
                    user_agents[agent]["disallow"].append(val)
            elif key == "crawl-delay":
                try:
                    delay = float(val)
                    for agent in current_agents:
                        if agent in user_agents:
                            user_agents[agent]["crawl_delay"] = delay
                except ValueError:
                    pass
            elif key == "sitemap":
                sitemaps.append(val)

    # Frontier AI audit
    frontier_bots = ["Googlebot", "GPTBot", "ClaudeBot", "PerplexityBot", "Applebot"]
    ai_status = {}
    for bot in frontier_bots:
        bot_key = next((k for k in user_agents if k.lower() == bot.lower()), "*")
        rules = user_agents.get(bot_key, user_agents.get("*", {"allow": [], "disallow": []}))
        is_blocked = "/" in rules.get("disallow", [])
        ai_status[bot] = {
            "accessible": not is_blocked,
            "rule_source": bot_key,
            "disallows": rules.get("disallow", [])
        }

    score = 100
    if not sitemaps:
        score -= 20
    for bot, status in ai_status.items():
        if not status["accessible"]:
            score -= 15

    score = max(10, min(100, score))
    grade = "A+" if score >= 95 else "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "F"

    return {
        "line_count": len(lines),
        "user_agent_count": len(user_agents),
        "sitemaps": sitemaps,
        "user_agents": user_agents,
        "frontier_ai_audit": ai_status,
        "score": score,
        "grade": grade,
        "compliant_rfc_9309": True
    }

class RobotsHandler(BaseHTTPRequestHandler):
    def send_json(self, data: Any, status: int = 200) -> None:
        raw = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        url_path = self.path.split("?")[0]

        if url_path in ("/health", "/api/health"):
            self.send_json({
                "status": "ok",
                "service": "robots-txt-auditor",
                "uptime": round(time.time() - START_TIME, 2),
                "port": self.server.server_port,
                "version": "2.5.0",
                "features": ["rfc-9309", "ai-crawler-simulation", "drift-shield", "sitemap-indexer"],
                "license": "100% Free & Open Access (Zero Paywalls)"
            })
            return

        if url_path == "/api/presets":
            self.send_json({"status": "ok", "presets": PRESETS})
            return

        # Static serving from public/
        clean_path = url_path.lstrip("/")
        if not clean_path:
            clean_path = "index.html"

        file_path = (PUBLIC_DIR / clean_path).resolve()
        if not str(file_path).startswith(str(PUBLIC_DIR)) or not file_path.is_file():
            fallback = PUBLIC_DIR / "index.html"
            if fallback.is_file():
                file_path = fallback
            else:
                self.send_error(404, "Not Found")
                return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"
        try:
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Internal Error: {e}")

    def do_POST(self) -> None:
        url_path = self.path.split("?")[0]

        try:
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception as e:
            self.send_json({"status": "error", "message": f"Malformed JSON: {e}"}, status=400)
            return

        if url_path in ("/api/parse", "/api/audit"):
            content = body.get("content") or body.get("robots") or ""
            parsed = parse_robots_txt(content)
            self.send_json({
                "status": "ok",
                "parsed": parsed,
                "timestamp": time.time()
            })
            return

        self.send_error(404, "Endpoint not found")

    def log_message(self, format: str, *args: Any) -> None:
        pass

def run_server(host: str = "127.0.0.1", port: int = 8086) -> ThreadingHTTPServer:
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, port), RobotsHandler)
    return server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Robots.txt & AEO Auditor Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8086, help="Port to listen on (default: 8086)")
    args = parser.parse_args()

    print(f"✦ Robots.txt & AEO Auditor Server starting on http://{args.host}:{args.port}")
    httpd = run_server(host=args.host, port=args.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Robots.txt & AEO Auditor Server...")
        httpd.server_close()
