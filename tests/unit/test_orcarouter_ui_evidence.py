# SecScan AI core module
"""Generate the OrcaRouter Cyber Inference UI evidence from the real dashboard.

This test starts the project's own web dashboard, drives it in headless
Chromium, and writes ``orca-evidence/manifest.json`` plus the screenshots used
by the pull request.  The evidence is produced here at verification time and is
deliberately not committed to the repository.

Only fake test data is typed into the key field.  When the operator credential
is configured in the environment the dropdown is populated from the live
OrcaRouter catalog; otherwise the dashboard shows its labelled degraded seed and
the assertions still hold because both the API response and the selector come
from the same backend call.
"""

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "orca-evidence"
BASE_URL = "http://127.0.0.1:8080"
CATALOG_SOURCE = "https://api.orcarouter.ai/v1/models?capability=chat"
TEST_KEY = "sk-orca-ui-evidence-only-0000"

playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="playwright is required for the UI evidence"
)

if not Path("/usr/bin/chromium").exists():
    pytest.skip(
        "chromium browser executable is not installed at /usr/bin/chromium",
        allow_module_level=True,
    )


def _dashboard_ready() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/ai/providers", timeout=2) as res:
            return res.status == 200
    except OSError:
        return False


def _port_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", 8080)) == 0


def _wait_for_dashboard(process=None, log_path=None, timeout: float = 90.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _dashboard_ready():
            return
        if process is not None and process.poll() is not None:
            raise AssertionError(
                "the SecScan AI dashboard exited with code "
                f"{process.returncode}: {_tail(log_path)}"
            )
        time.sleep(0.5)
    raise AssertionError(
        "the SecScan AI dashboard did not become ready on :8080: " + _tail(log_path)
    )


def _tail(log_path) -> str:
    if log_path is None or not log_path.exists():
        return "<no output captured>"
    return log_path.read_text(errors="replace")[-2000:]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _launch_dashboard():
    """Start the dashboard unless another instance is already serving it."""
    if _dashboard_ready():
        return None, None
    assert not _port_open(), "port 8080 is occupied by a non-SecScan AI service"
    env = os.environ.copy()
    env.setdefault("SECSCAN_AI_DISABLE_ANIMATION", "1")
    log_path = Path(tempfile.gettempdir()) / "secscan_ai-dashboard.log"
    log_handle = log_path.open("wb")
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "advance_secscan_ai.py"), "--web"],
        cwd=str(ROOT),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        _wait_for_dashboard(process, log_path)
    except Exception:
        _stop_dashboard(process)
        log_handle.close()
        raise
    return process, log_handle


def _stop_dashboard(process) -> None:
    if process is None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def test_gui_evidence_matches_live_catalog():
    process, log_handle = _launch_dashboard()
    try:
        proxy_server = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        proxy = (
            {"server": proxy_server, "bypass": "127.0.0.1,localhost"}
            if proxy_server
            else None
        )
        with playwright_api.sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=["--no-sandbox", "--disable-dev-shm-usage"],
                proxy=proxy,
            )
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 960})
                page.goto(BASE_URL, wait_until="commit", timeout=45000)
                page.wait_for_selector('[data-view="ai-providers"]', timeout=60000)

                page.click('[data-view="ai-providers"]')
                page.wait_for_selector("#view-ai-providers.active")
                page.wait_for_selector(
                    "#ai-provider-select option[value='orcarouter']", state="attached"
                )
                page.wait_for_function(
                    "() => !/Loading model catalog/.test("
                    "document.getElementById('ai-model-status').innerText)",
                    timeout=45000,
                )

                catalog = page.evaluate("""async () => {
                        const res = await fetch(
                            '/api/ai/models?provider=orcarouter&capability=chat');
                        return {status: res.status, body: await res.json()};
                    }""")["body"]
                api_ids = [m["id"] for m in catalog.get("models", [])]

                image_catalog = page.evaluate("""async () => {
                        const res = await fetch(
                            '/api/ai/models?provider=orcarouter&capability=image');
                        return {status: res.status, body: await res.json()};
                    }""")["body"]

                # Dedicated test data in the (password) key field for the auth shot.
                page.fill("#orcarouter-api-key", TEST_KEY)

                auth_assertions = page.evaluate(
                    """(testKey) => {
                        const input = document.getElementById('orcarouter-api-key');
                        const save = document.getElementById('orcarouter-save-key');
                        const refresh = document.getElementById('ai-model-refresh');
                        const trigger = document.getElementById('ai-model-trigger');
                        const bodyText = document.body.innerText;
                        return {
                            api_key_visible: !!(input && input.offsetParent !== null),
                            input_is_password: input ? input.type === 'password' : false,
                            secret_masked: !bodyText.includes(testKey),
                            controls_enabled: !!(save && !save.disabled && refresh &&
                                !refresh.disabled && trigger && !trigger.disabled),
                            provider_label: document
                                .getElementById('ai-provider-select')
                                .selectedOptions[0].textContent.trim(),
                        };
                    }""",
                    TEST_KEY,
                )
                assert auth_assertions["api_key_visible"]
                assert auth_assertions["input_is_password"]
                assert auth_assertions["secret_masked"]
                assert auth_assertions["controls_enabled"]
                assert auth_assertions["provider_label"] == "OrcaRouter Cyber Inference"

                OUT_DIR.mkdir(parents=True, exist_ok=True)
                auth_path = OUT_DIR / "auth-methods.png"
                page.screenshot(path=str(auth_path), full_page=False)

                # Clear the test value before opening the real catalog dropdown.
                page.fill("#orcarouter-api-key", "")

                page.click("#ai-model-trigger")
                page.wait_for_selector("#ai-model-panel:not([hidden])")
                page.wait_for_function(
                    "() => document.querySelectorAll('#ai-model-panel .orca-option')"
                    ".length > 0",
                    timeout=15000,
                )

                dropdown = page.evaluate("""() => {
                        const panel = document.getElementById('ai-model-panel');
                        const trigger = document.getElementById('ai-model-trigger');
                        const style = getComputedStyle(panel);
                        const triggerBox = trigger.getBoundingClientRect();
                        const panelBox = panel.getBoundingClientRect();
                        const options = Array.from(
                            panel.querySelectorAll('.orca-option'));
                        return {
                            dropdown_open: !panel.hasAttribute('hidden') &&
                                panelBox.height > 0,
                            item_count: options.length,
                            option_ids: options.map(o => o.dataset.modelId),
                            background_color: style.backgroundColor,
                            border_width: style.borderTopWidth,
                            border_style: style.borderTopStyle,
                            trigger_panel_right_delta:
                                Math.abs(panelBox.right - triggerBox.right),
                        };
                    }""")
                assert dropdown["dropdown_open"]
                assert dropdown["item_count"] >= 5
                assert dropdown["item_count"] == len(api_ids), (
                    "selector options do not match the API catalog: "
                    f"{dropdown['item_count']} vs {len(api_ids)}"
                )
                assert dropdown["option_ids"] == api_ids
                assert (
                    dropdown["border_style"] != "none"
                    and float(dropdown["border_width"].replace("px", "")) > 0
                )
                assert dropdown["background_color"].startswith("rgb(")
                assert dropdown["trigger_panel_right_delta"] <= 2

                dropdown_path = OUT_DIR / "text-model-dropdown.png"
                page.evaluate(
                    "document.getElementById('ai-model-panel')"
                    ".scrollIntoView({block: 'center'})"
                )
                page.wait_for_timeout(250)
                page.screenshot(path=str(dropdown_path), full_page=False)

                viewport = page.viewport_size
                assert viewport["width"] >= 800 and viewport["height"] >= 450
            finally:
                browser.close()

        opaque_background = dropdown["background_color"].startswith("rgb(")
        visible_border = (
            dropdown["border_style"] != "none"
            and float(dropdown["border_width"].replace("px", "")) > 0
        )
        artifacts = [
            {
                "kind": "auth-methods",
                "path": "auth-methods.png",
                "sha256": _sha256(OUT_DIR / "auth-methods.png"),
                "ui": {
                    "api_key_visible": auth_assertions["api_key_visible"],
                    "secret_masked": auth_assertions["secret_masked"],
                    "controls_enabled": auth_assertions["controls_enabled"],
                    "provider_label": auth_assertions["provider_label"],
                },
            },
            {
                "kind": "text-model-dropdown",
                "path": "text-model-dropdown.png",
                "sha256": _sha256(OUT_DIR / "text-model-dropdown.png"),
                "ui": {
                    "dropdown_open": dropdown["dropdown_open"],
                    "item_count": dropdown["item_count"],
                    "opaque_background": opaque_background,
                    "visible_border": visible_border,
                    "trigger_panel_right_delta": round(
                        dropdown["trigger_panel_right_delta"], 2
                    ),
                    "options_match_api_catalog": True,
                },
            },
        ]
        manifest = {
            "automation": {
                "framework": "playwright",
                "passed": True,
                "catalog_source": CATALOG_SOURCE,
                "catalog_model_count": len(api_ids),
                "image_model_count": len(image_catalog.get("models", [])),
                "catalog_degraded": bool(catalog.get("degraded")),
                "script": "tests/unit/test_orcarouter_ui_evidence.py",
                "multimodal": False,
                "multimodal_reason": (
                    "SecScan AI's AI entry points call text-only chat_completion; "
                    "there is no image/audio/video attachment input to filter, so "
                    "no multimodal selector exists."
                ),
            },
            "artifacts": artifacts,
        }
        (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    finally:
        _stop_dashboard(process)
        if log_handle is not None:
            log_handle.close()
