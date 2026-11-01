"""Automated pytest verification suite for robots-txt-auditor."""
import json
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from server import PRESETS, parse_robots_txt, run_server


def test_presets_defined():
    assert "open_sovereign" in PRESETS
    assert "stealth_disallow" in PRESETS
    assert "selective_ai" in PRESETS
    for key, val in PRESETS.items():
        assert "name" in val
        assert "content" in val
        assert "User-agent:" in val["content"]


def test_parse_open_sovereign():
    res = parse_robots_txt(PRESETS["open_sovereign"]["content"])
    assert res["compliant_rfc_9309"] is True
    assert res["score"] == 100
    assert res["grade"] == "A+"
    assert "https://nullai.tech/sitemap.xml" in res["sitemaps"]
    for bot in ["Googlebot", "GPTBot", "ClaudeBot", "PerplexityBot", "Applebot"]:
        assert res["frontier_ai_audit"][bot]["accessible"] is True


def test_parse_stealth_disallow():
    res = parse_robots_txt(PRESETS["stealth_disallow"]["content"])
    assert res["compliant_rfc_9309"] is True
    assert res["sitemaps"] == []
    assert res["score"] < 50
    assert res["grade"] == "F"
    for bot in ["Googlebot", "GPTBot", "ClaudeBot", "PerplexityBot", "Applebot"]:
        assert res["frontier_ai_audit"][bot]["accessible"] is False


def test_parse_selective_ai():
    res = parse_robots_txt(PRESETS["selective_ai"]["content"])
    assert res["score"] == 100
    assert res["grade"] == "A+"
    assert res["frontier_ai_audit"]["GPTBot"]["accessible"] is True
    assert "/internal/" in res["frontier_ai_audit"]["GPTBot"]["disallows"]


def test_parse_crawl_delay_and_comments():
    raw = """# Comment header
User-agent: *
Crawl-delay: 2.5
Allow: /public/
Disallow: /secret/
Sitemap: https://example.com/sitemap.xml
"""
    res = parse_robots_txt(raw)
    assert res["user_agents"]["*"]["crawl_delay"] == 2.5
    assert "/public/" in res["user_agents"]["*"]["allow"]
    assert "/secret/" in res["user_agents"]["*"]["disallow"]
    assert res["sitemaps"] == ["https://example.com/sitemap.xml"]


def test_cli_presets_and_audit():
    cli_bin = REPO_DIR / "bin" / "robots-txt-auditor"
    out = subprocess.check_output([sys.executable, str(cli_bin), "--presets"], text=True)
    assert "open_sovereign" in out
    assert "selective_ai" in out

    out_audit = subprocess.check_output(
        [sys.executable, str(cli_bin), "--preset", "open_sovereign"], text=True
    )
    assert "100/100 (A+)" in out_audit
    assert "Googlebot" in out_audit
    assert "GPTBot" in out_audit


def test_cli_audit_json():
    cli_bin = REPO_DIR / "bin" / "robots-txt-auditor"
    out_json = subprocess.check_output(
        [sys.executable, str(cli_bin), "--audit", "selective_ai", "--json"], text=True
    )
    data = json.loads(out_json)
    assert data["status"] == "ok"
    assert data["parsed"]["grade"] == "A+"


def test_http_server_endpoints():
    server = run_server(host="127.0.0.1", port=18086)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        time.sleep(0.2)
        with urllib.request.urlopen("http://127.0.0.1:18086/health", timeout=2) as resp:
            health = json.loads(resp.read().decode("utf-8"))
            assert health["status"] == "ok"
            assert health["service"] == "robots-txt-auditor"

        with urllib.request.urlopen("http://127.0.0.1:18086/api/presets", timeout=2) as resp:
            presets = json.loads(resp.read().decode("utf-8"))
            assert presets["status"] == "ok"
            assert "open_sovereign" in presets["presets"]

        req = urllib.request.Request(
            "http://127.0.0.1:18086/api/audit",
            data=json.dumps({"content": PRESETS["open_sovereign"]["content"]}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            audit = json.loads(resp.read().decode("utf-8"))
            assert audit["status"] == "ok"
            assert audit["parsed"]["score"] == 100

        with urllib.request.urlopen("http://127.0.0.1:18086/", timeout=2) as resp:
            html = resp.read().decode("utf-8")
            assert "RobotsTxt Pro" in html
            assert "100% FREE &amp; OPEN ACCESS" in html
    finally:
        server.shutdown()
        server.server_close()
