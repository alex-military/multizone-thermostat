"""Test frontend bundler and bundle consistency."""
import subprocess
import sys
from pathlib import Path

from frontend.build import assemble_bundle, build, SRC_FILES


def test_frontend_bundle_all_sources_exist():
    """Verify all defined source files exist and are not empty."""
    root = Path(__file__).resolve().parent.parent
    src_dir = root / "frontend" / "src"

    assert len(SRC_FILES) >= 10
    for rel in SRC_FILES:
        f = src_dir / rel
        assert f.is_file(), f"Source file missing: {f}"
        assert f.stat().st_size > 0, f"Source file is empty: {f}"


def test_frontend_bundle_contains_all_components():
    """Verify the assembled bundle registers all essential custom elements."""
    bundle = assemble_bundle()
    assert len(bundle) > 50000

    essential_tags = [
        "multizone-thermostat-button-card",
        "multizone-thermostat-dial-card",
        "multizone-thermostat-status-card",
        "multizone-thermostat-card-editor",
        "multizone-thermostat-preset-card",
        "multizone-thermostat-spacer",
        "multizone-thermostat-schedule-summary-card",
        "multizone-thermostat-health-summary-card",
        "multizone-thermostat-nav-card",
        "multizone-thermostat-responsive-grid",
        "multizone-thermostat-plant-card",
        "multizone-thermostat-zone-energy-card",
        "multizone-thermostat-scheduler-card",
        "multizone-thermostat-style-switcher",
        "ll-strategy-dashboard-multizone-thermostat-dashboard",
    ]

    for tag in essential_tags:
        assert tag in bundle, f"Expected custom element tag '{tag}' in bundle"


def test_frontend_bundler_check_mode():
    """Verify that build(check_only=True) succeeds."""
    assert build(check_only=True) is True
