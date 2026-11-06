"""
OpenOS Installer AI Agent.

Wraps the OpenOSBrain specifically for the installation flow.
"""

from __future__ import annotations

import logging

from openos_core.brain.engine import OpenOSBrain
from openos_core.brain.router import ToolRouter
from openos_core.config import get_config
from openos_installer.config import InstallConfig
from openos_installer.tools import InstallerTool

logger = logging.getLogger(__name__)

INSTALLER_SYSTEM_PROMPT = """\
You are the OpenOS Installer Assistant. Your goal is to guide the user through installing OpenOS on their machine.

Instead of a traditional graphical wizard with forms, you will chat with the user to gather the following required information:
1. **Target Disk**: Use `list_disks` to show available drives and ask which one to use.
2. **Timezone**: Ask for their timezone (e.g., America/New_York or Europe/London).
3. **Username**: Ask what they want their username to be.
4. **Password**: Ask for a secure password.
5. **Hostname**: Ask what they want to name their computer (default is openos).

Guidelines:
- Be friendly, encouraging, and clear.
- Guide the user one step at a time. Don't ask for everything at once.
- Use `set_install_config` to save the information as you gather it.
- Use `get_missing_config` to check what you still need.
- Once EVERYTHING is gathered, summarize their choices and explicitly ask "Are you ready to begin the installation? This will format the selected disk."
- ONLY when they confirm, use `start_installation` to begin.

Start by welcoming the user to the OpenOS Installer and asking if they want to see the available disks.
"""


class InstallerAgent:
    """Specialized agent for the OS installer."""

    def __init__(self, config: InstallConfig):
        self.install_config = config
        self._brain: OpenOSBrain | None = None
        self._installer_tool = InstallerTool(config)

    def set_callbacks(self, on_state_change, on_start_install):
        self._installer_tool.set_callbacks(on_state_change, on_start_install)

    async def initialize(self) -> bool:
        """Initialize the Brain for the installer."""
        try:
            self._brain = OpenOSBrain()

            # Use custom router with ONLY the installer tool
            # (We don't want the installer AI randomly launching apps or pausing music)
            custom_router = ToolRouter()
            custom_router._register_tool(self._installer_tool)

            # Manually inject router and system prompt
            self._brain._router = custom_router

            # Recreate backend
            global_config = get_config()
            self._brain._backend = self._brain._create_backend(
                global_config.llm.backend,
                global_config.llm.host,
                global_config.llm.api_key,
            )
            self._brain._model = global_config.llm.default_model

            # Set the custom prompt
            tool_schemas = custom_router.get_tool_descriptions()
            prompt = INSTALLER_SYSTEM_PROMPT + f"\n\nAvailable Tools:\n{tool_schemas}"
            self._brain._messages = [{"role": "system", "content": prompt}]

            self._brain._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Installer Agent: {e}")
            return False

    async def process(self, text: str) -> str:
        """Process user input and return the AI's response."""
        if not self._brain or not self._brain._initialized:
            return "AI Engine is not initialized."

        try:
            result = await self._brain.process(text)
            return str(result.get("response", "No response generated."))
        except Exception as e:
            return f"Error: {str(e)}"
