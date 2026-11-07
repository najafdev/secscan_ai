"""
HackBot Core Module
"""

from hackbot.core.engine import AIEngine, Conversation, Message, create_conversation
from hackbot.core.runner import ToolRunner
from hackbot.core.vulndb import VulnDB
from hackbot.core.zeroday import ZeroDayEngine
from hackbot.core.rag_memory import RAGMemory, get_rag_memory
from hackbot.core.zeroday_active import (
    ActiveScanLoop,
    HttpClient,
    ParallelExecutor,
    StatefulFuzzer,
    TargetMapper,
)

__all__ = [
    "AIEngine", "Conversation", "Message", "create_conversation",
    "ToolRunner", "VulnDB", "ZeroDayEngine",
    "RAGMemory", "get_rag_memory",
    "ActiveScanLoop", "HttpClient", "ParallelExecutor", "StatefulFuzzer", "TargetMapper",
]
