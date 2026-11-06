"""
OpenOS Screen Reader Tool.

Captures screenshots and sends them to the vision-capable LLM for analysis.
Supports:
  - Full screen capture
  - Active window capture
  - Region selection
  - OCR text extraction (fallback)

Works on both Wayland (grim/slurp) and X11 (scrot/import).
"""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from typing import Any

from openos_core.tools.base import BaseTool, tool_function


class ScreenReaderTool(BaseTool):
    """Capture and analyze screen content using AI vision."""

    @property
    def name(self) -> str:
        return "screen_reader"

    @property
    def description(self) -> str:
        return "Capture screenshots and analyze screen content using AI vision"

    def _detect_display_server(self) -> str:
        """Detect whether we're running Wayland or X11."""
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        elif os.environ.get("DISPLAY"):
            return "x11"
        return "unknown"

    def _get_screenshot_tool(self, mode: str = "full") -> tuple[str, list[str]] | None:
        """Find available screenshot tool and build command."""
        server = self._detect_display_server()

        if server == "wayland":
            if shutil.which("grim"):
                if mode == "region" and shutil.which("slurp"):
                    return ("grim_slurp", ["grim", "-g", "$(slurp)"])
                elif mode == "window" and shutil.which("slurp"):
                    # Use slurp in window-select mode
                    return ("grim_slurp", ["grim", "-g", "$(slurp)"])
                else:
                    return ("grim", ["grim"])
            elif shutil.which("gnome-screenshot"):
                return ("gnome-screenshot", ["gnome-screenshot", "-f"])
        elif server == "x11":
            if shutil.which("scrot"):
                if mode == "window":
                    return ("scrot", ["scrot", "-u"])  # Active window
                elif mode == "region":
                    return ("scrot", ["scrot", "-s"])  # Select region
                else:
                    return ("scrot", ["scrot"])
            elif shutil.which("import"):
                if mode == "window":
                    return ("import", ["import", "-window", "root"])
                else:
                    return ("import", ["import", "-window", "root"])
            elif shutil.which("gnome-screenshot"):
                return ("gnome-screenshot", ["gnome-screenshot", "-f"])

        # Fallback: try any available tool
        for tool_name in ["grim", "scrot", "gnome-screenshot"]:
            if shutil.which(tool_name):
                if tool_name == "gnome-screenshot":
                    return (tool_name, [tool_name, "-f"])
                return (tool_name, [tool_name])

        return None

    def _capture_screenshot(self, mode: str = "full") -> str | None:
        """Capture a screenshot and return the file path."""
        tool_info = self._get_screenshot_tool(mode)
        if not tool_info:
            return None

        tool_name, cmd = tool_info

        # Create temp file for the screenshot
        tmp_dir = Path(tempfile.gettempdir()) / "openos-screenshots"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        filepath = str(tmp_dir / f"screen_{os.getpid()}.png")

        try:
            if tool_name == "grim":
                subprocess.run(cmd + [filepath], check=True, timeout=10)
            elif tool_name == "grim_slurp":
                # Need shell=True for command substitution
                shell_cmd = f"grim -g \"$(slurp)\" {filepath}"
                subprocess.run(shell_cmd, shell=True, check=True, timeout=30)
            elif tool_name == "scrot":
                subprocess.run(cmd + [filepath], check=True, timeout=10)
            elif tool_name == "import":
                subprocess.run(cmd + [filepath], check=True, timeout=10)
            elif tool_name == "gnome-screenshot":
                subprocess.run(cmd + [filepath], check=True, timeout=10)
            else:
                return None

            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return filepath
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # Cleanup on failure
            if os.path.exists(filepath):
                os.unlink(filepath)
            return None

        return None

    def _image_to_base64(self, filepath: str) -> str:
        """Convert an image file to base64-encoded data URI."""
        with open(filepath, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode("utf-8")

        # Detect mime type
        if filepath.endswith(".png"):
            mime = "image/png"
        elif filepath.endswith((".jpg", ".jpeg")):
            mime = "image/jpeg"
        else:
            mime = "image/png"

        return f"data:{mime};base64,{b64}"

    def _extract_text_ocr(self, filepath: str) -> str | None:
        """Try to extract text from image using tesseract OCR (fallback)."""
        if not shutil.which("tesseract"):
            return None
        try:
            result = subprocess.run(
                ["tesseract", filepath, "-", "--oem", "3", "--psm", "3"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
        return None

    @tool_function(
        description="Take a screenshot of the entire screen and analyze what's visible using AI vision",
        parameters={
            "question": {
                "type": "string",
                "description": "What to look for or ask about the screen content (e.g., 'what error is shown?', 'summarize the article', 'read the code')",
            },
        },
    )
    def analyze_screen(self, question: str = "Describe what you see on the screen") -> str:
        """Capture full screen and analyze with vision AI."""
        return self._analyze(mode="full", question=question)

    @tool_function(
        description="Take a screenshot of the active/focused window and analyze its content",
        parameters={
            "question": {
                "type": "string",
                "description": "What to ask about the window content",
            },
        },
    )
    def analyze_window(self, question: str = "Describe what's in this window") -> str:
        """Capture active window and analyze with vision AI."""
        return self._analyze(mode="window", question=question)

    @tool_function(
        description="Let the user select a region of the screen to analyze (interactive selection)",
        parameters={
            "question": {
                "type": "string",
                "description": "What to ask about the selected region",
            },
        },
    )
    def analyze_region(self, question: str = "What do you see in this region?") -> str:
        """Capture a user-selected region and analyze with vision AI."""
        return self._analyze(mode="region", question=question)

    @tool_function(
        description="Extract readable text from the current screen using OCR (no AI needed)",
        parameters={},
    )
    def read_screen_text(self) -> str:
        """Capture screen and extract text using OCR."""
        filepath = self._capture_screenshot(mode="full")
        if not filepath:
            return "❌ Could not capture screenshot. No screenshot tool found (install grim or scrot)."

        try:
            text = self._extract_text_ocr(filepath)
            if text:
                return f"📄 Extracted text from screen:\n\n{text}"
            else:
                return "⚠️ Could not extract text. Install tesseract: sudo apt install tesseract-ocr"
        finally:
            # Cleanup
            if os.path.exists(filepath):
                os.unlink(filepath)

    @tool_function(
        description="Take a screenshot and save it to a file",
        parameters={
            "save_path": {
                "type": "string",
                "description": "Where to save the screenshot (default: ~/Pictures/screenshot.png)",
                "optional": True,
            },
        },
    )
    def take_screenshot(self, save_path: str = "") -> str:
        """Take a screenshot and save it."""
        filepath = self._capture_screenshot(mode="full")
        if not filepath:
            return "❌ Could not capture screenshot. No screenshot tool found."

        if not save_path:
            pictures_dir = Path.home() / "Pictures"
            pictures_dir.mkdir(exist_ok=True)
            import time
            save_path = str(pictures_dir / f"screenshot-{int(time.time())}.png")

        try:
            shutil.copy2(filepath, save_path)
            return f"📸 Screenshot saved to: {save_path}"
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def _analyze(self, mode: str, question: str) -> str:
        """Core analysis: capture → encode → send to vision LLM."""
        filepath = self._capture_screenshot(mode=mode)
        if not filepath:
            return (
                "❌ Could not capture screenshot.\n"
                "Install a screenshot tool:\n"
                "  Wayland: sudo apt install grim slurp\n"
                "  X11: sudo apt install scrot"
            )

        try:
            image_data_uri = self._image_to_base64(filepath)

            # Send to vision LLM
            from openos_core.config import get_config
            config = get_config()

            if config.llm.backend in ("openai", "copilot-api", "lmstudio", "vllm"):
                return self._analyze_openai(config, image_data_uri, question)
            elif config.llm.backend == "ollama":
                return self._analyze_ollama(config, filepath, question)
            else:
                # Fallback to OCR
                text = self._extract_text_ocr(filepath)
                if text:
                    return f"📄 OCR extracted text:\n\n{text}\n\n(Vision API not available for backend: {config.llm.backend})"
                return f"⚠️ Vision not supported for backend: {config.llm.backend}"
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def _analyze_openai(self, config, image_data_uri: str, question: str) -> str:
        """Analyze screenshot using OpenAI-compatible vision API."""
        from openai import OpenAI

        key = config.llm.api_key or "sk-local-proxy"
        base_url = config.llm.host.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"

        client = OpenAI(base_url=base_url, api_key=key)

        # Use the vision-capable model
        model = config.llm.default_model

        messages: list[Any] = [
            {
                "role": "system",
                "content": (
                    "You are OpenOS, an AI operating system assistant analyzing the user's screen. "
                    "Describe what you see concisely and answer the user's question. "
                    "If there's an error, explain it clearly. "
                    "If there's code, provide helpful analysis. "
                    "Be specific about UI elements, text content, and application state."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": question,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_uri,
                            "detail": "high",
                        },
                    },
                ],
            },
        ]

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1024,
                temperature=0.3,
            )
            content = response.choices[0].message.content
            return f"👁️ Screen Analysis:\n\n{content}"
        except Exception as e:
            # Fallback to OCR if vision API fails
            error_msg = str(e)
            if "vision" in error_msg.lower() or "image" in error_msg.lower() or "400" in error_msg:
                return (
                    f"⚠️ Vision API not supported by this endpoint.\n"
                    f"Error: {error_msg[:200]}\n\n"
                    "Tip: Use a vision-capable model (gpt-4o, llava, etc.)"
                )
            return f"❌ Vision analysis failed: {error_msg[:200]}"

    def _analyze_ollama(self, config, filepath: str, question: str) -> str:
        """Analyze screenshot using Ollama vision models (llava, etc.)."""
        try:
            import ollama

            # Read the raw image bytes for Ollama
            with open(filepath, "rb") as f:
                image_data = f.read()

            # Use a vision model — llava is the standard Ollama vision model
            vision_model = config.llm.default_model
            # Auto-suggest vision model if using a text-only model
            text_only_models = ["llama", "qwen", "mistral", "gemma", "phi"]
            if any(m in vision_model.lower() for m in text_only_models):
                vision_model = "llava:7b"

            client = ollama.Client(host=config.llm.host)
            response = client.chat(
                model=vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": question,
                        "images": [image_data],
                    }
                ],
            )
            content = response.message.content
            return f"👁️ Screen Analysis:\n\n{content}"
        except Exception as e:
            return (
                f"❌ Ollama vision failed: {e}\n"
                "Tip: Install a vision model: ollama pull llava:7b"
            )
