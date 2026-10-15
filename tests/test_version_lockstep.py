"""Version lockstep — every version surface reports the same version."""

from __future__ import annotations

import json
import shutil
import subprocess
import tomllib
import unittest
from pathlib import Path

from typer.testing import CliRunner

import dropbrief
from dropbrief import fetch
from dropbrief.cli import app

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED = "0.3.0"


def test_version_file():
    assert (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() == EXPECTED


def test_pyproject_version():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == EXPECTED


def test_dunder_version():
    assert dropbrief.__version__ == EXPECTED


def test_user_agent_tracks_version():
    assert fetch.USER_AGENT.startswith(f"dropbrief/{EXPECTED}")


def test_site_json_content_version():
    site = json.loads((REPO_ROOT / "web" / "site.json").read_text(encoding="utf-8"))
    assert site["meta"]["content_version"] == EXPECTED


def test_changelog_has_both_sections():
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[0.2.0]" in text
    assert "[0.3.0]" in text


def test_changelog_has_release_link_for_current_version():
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert (
        f"[{EXPECTED}]: https://github.com/SuperMarioYL/dropbrief/compare/"
        in text
    )


def test_cli_version_flag():
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"dropbrief {EXPECTED}" in result.output


def test_cli_version_subcommand():
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"dropbrief {EXPECTED}" in result.output


@unittest.skipUnless(shutil.which("dropbrief"), "dropbrief console script not on PATH")
def test_installed_console_script_version():
    out = subprocess.run(
        ["dropbrief", "--version"], capture_output=True, text=True, timeout=30
    )
    assert out.returncode == 0
    assert f"dropbrief {EXPECTED}" in out.stdout
