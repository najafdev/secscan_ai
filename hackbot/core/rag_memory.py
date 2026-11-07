"""
HackBot RAG Memory (ChromaDB)
==============================
Retrieval-Augmented Generation memory system that provides persistent,
semantic search over past conversations, findings, tool outputs, and
security knowledge.

Uses ChromaDB with local sentence-transformer embeddings — no API key
required for embeddings.  All data is stored locally at
``~/.config/hackbot/chromadb/``.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from hackbot.config import CONFIG_DIR

logger = logging.getLogger(__name__)

# ── Availability flag ────────────────────────────────────────────────────────

try:
    import chromadb  # type: ignore[import-untyped]
    from chromadb.config import Settings  # type: ignore[import-untyped]

    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

# ── Constants ────────────────────────────────────────────────────────────────

CHROMADB_DIR = CONFIG_DIR / "chromadb"
COLLECTION_NAME = "hackbot_memory"

# Document type tags
DOC_CONVERSATION = "conversation"
DOC_FINDING = "finding"
DOC_TOOL_OUTPUT = "tool_output"
DOC_KNOWLEDGE = "knowledge"


# ── Data types ───────────────────────────────────────────────────────────────

@dataclass
class RAGResult:
    """A single retrieval result from the vector store."""
    text: str
    doc_type: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "doc_type": self.doc_type,
            "score": round(self.score, 4),
            "metadata": self.metadata,
        }


# ── Chunking Utilities ───────────────────────────────────────────────────────

def _chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[str]:
    """Split *text* into overlapping word-level chunks.

    Args:
        text: The text to split.
        chunk_size: Target number of words per chunk.
        chunk_overlap: Number of overlapping words between chunks.

    Returns:
        List of text chunks.  Short texts are returned as a single chunk.
    """
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - chunk_overlap

    return chunks


def _doc_id(text: str, prefix: str = "") -> str:
    """Deterministic document ID from content hash."""
    h = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"{prefix}_{h}" if prefix else h


# ── RAG Memory Engine ────────────────────────────────────────────────────────

class RAGMemory:
    """ChromaDB-backed vector memory for semantic retrieval.

    Usage::

        rag = RAGMemory()
        if rag.is_available():
            rag.store_conversation("user", "How do I scan for open ports?", session_id="chat_123")
            results = rag.query("port scanning")
            context = rag.get_context("nmap scan results")
    """

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        collection_name: str = COLLECTION_NAME,
    ):
        self._persist_dir = persist_dir or CHROMADB_DIR
        self._collection_name = collection_name
        self._client: Any = None
        self._collection: Any = None
        self._available = False

        if HAS_CHROMADB:
            self._init_chromadb()

    # ── Initialisation ───────────────────────────────────────────────────

    def _init_chromadb(self) -> None:
        """Create or open the persistent ChromaDB collection."""
        try:
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self._persist_dir),
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
            logger.debug(
                "RAG memory initialised — %d documents in collection '%s'",
                self._collection.count(),
                self._collection_name,
            )
        except Exception as exc:
            logger.warning("Failed to initialise ChromaDB RAG memory: %s", exc)
            self._available = False

    def is_available(self) -> bool:
        """Return True if the vector store is ready."""
        return self._available

    # ── Core store / query ───────────────────────────────────────────────

    def store(
        self,
        text: str,
        doc_type: str = DOC_KNOWLEDGE,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> int:
        """Embed and store *text* (optionally chunked).

        Returns the number of chunks stored.
        """
        if not self._available or not text.strip():
            return 0

        meta = {
            "doc_type": doc_type,
            "timestamp": time.time(),
        }
        if metadata:
            # ChromaDB metadata values must be str | int | float | bool
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                else:
                    meta[k] = str(v)

        chunks = _chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for i, chunk in enumerate(chunks):
            doc_id = _doc_id(chunk, prefix=doc_type)
            ids.append(doc_id)
            documents.append(chunk)
            chunk_meta = dict(meta)
            chunk_meta["chunk_index"] = i
            chunk_meta["total_chunks"] = len(chunks)
            metadatas.append(chunk_meta)

        try:
            self._collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as exc:
            logger.warning("RAG store failed: %s", exc)
            return 0

        return len(chunks)

    def query(
        self,
        text: str,
        n_results: int = 5,
        doc_type: Optional[str] = None,
    ) -> List[RAGResult]:
        """Semantic search for documents related to *text*.

        Args:
            text: The query string.
            n_results: Maximum results to return.
            doc_type: Optional filter by document type.

        Returns:
            List of :class:`RAGResult` ordered by relevance (best first).
        """
        if not self._available or not text.strip():
            return []

        where_filter = None
        if doc_type:
            where_filter = {"doc_type": doc_type}

        try:
            results = self._collection.query(
                query_texts=[text],
                n_results=min(n_results, self._collection.count() or 1),
                where=where_filter if where_filter else None,
            )
        except Exception as exc:
            logger.warning("RAG query failed: %s", exc)
            return []

        output: List[RAGResult] = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
            metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)

            for doc, dist, meta in zip(docs, distances, metadatas):
                # ChromaDB returns cosine distance; convert to similarity score
                score = 1.0 - dist
                output.append(RAGResult(
                    text=doc,
                    doc_type=meta.get("doc_type", "unknown"),
                    score=score,
                    metadata=meta,
                ))

        return output

    # ── Convenience store methods ────────────────────────────────────────

    def store_conversation(
        self,
        role: str,
        content: str,
        session_id: str = "",
        mode: str = "chat",
        target: str = "",
    ) -> int:
        """Store a conversation message."""
        prefix = "User" if role == "user" else "Assistant"
        text = f"[{prefix}]: {content}"
        return self.store(
            text=text,
            doc_type=DOC_CONVERSATION,
            metadata={
                "role": role,
                "session_id": session_id,
                "mode": mode,
                "target": target,
            },
        )

    def store_finding(self, finding: Dict[str, Any]) -> int:
        """Store a security finding."""
        parts = [
            f"Finding: {finding.get('title', 'Unknown')}",
            f"Severity: {finding.get('severity', 'Info')}",
            f"Description: {finding.get('description', '')}",
        ]
        if finding.get("evidence"):
            parts.append(f"Evidence: {finding['evidence']}")
        if finding.get("recommendation"):
            parts.append(f"Recommendation: {finding['recommendation']}")

        text = "\n".join(parts)
        return self.store(
            text=text,
            doc_type=DOC_FINDING,
            metadata={
                "title": finding.get("title", ""),
                "severity": finding.get("severity", "Info"),
                "target": finding.get("target", ""),
                "tool": finding.get("tool", ""),
            },
        )

    def store_tool_output(
        self,
        command: str,
        stdout: str,
        stderr: str = "",
        target: str = "",
        tool: str = "",
        success: bool = True,
    ) -> int:
        """Store a tool execution result."""
        parts = [f"Command: {command}"]
        if stdout:
            parts.append(f"Output:\n{stdout}")
        if stderr:
            parts.append(f"Errors:\n{stderr}")

        text = "\n".join(parts)
        return self.store(
            text=text,
            doc_type=DOC_TOOL_OUTPUT,
            metadata={
                "command": command[:200],
                "target": target,
                "tool": tool,
                "success": success,
            },
        )

    # ── Context retrieval (for prompt injection) ─────────────────────────

    def get_context(
        self,
        query: str,
        max_results: int = 5,
        max_chars: int = 3000,
        min_score: float = 0.3,
    ) -> str:
        """Retrieve relevant context formatted for system prompt injection.

        Returns a formatted string of relevant past context, or an empty
        string if nothing relevant is found.
        """
        results = self.query(query, n_results=max_results)
        if not results:
            return ""

        # Filter by minimum relevance score
        relevant = [r for r in results if r.score >= min_score]
        if not relevant:
            return ""

        lines: List[str] = []
        total_chars = 0

        for r in relevant:
            entry = f"[{r.doc_type.upper()} | relevance: {r.score:.0%}]\n{r.text}"
            if total_chars + len(entry) > max_chars:
                break
            lines.append(entry)
            total_chars += len(entry)

        if not lines:
            return ""

        return (
            "[MEMORY CONTEXT — Retrieved from past sessions]\n"
            + "\n\n---\n\n".join(lines)
            + "\n[END MEMORY CONTEXT]"
        )

    def get_target_context(
        self,
        target: str,
        max_results: int = 8,
        max_chars: int = 4000,
    ) -> str:
        """Retrieve past findings and scan data for a specific target.

        Used when starting a new agent assessment against a previously
        scanned target.
        """
        if not self._available:
            return ""

        # Search for findings related to this target
        finding_results = self.query(
            f"target {target} findings vulnerabilities",
            n_results=max_results,
            doc_type=DOC_FINDING,
        )

        # Search for tool outputs related to this target
        tool_results = self.query(
            f"scan {target} nmap ports services",
            n_results=max_results // 2,
            doc_type=DOC_TOOL_OUTPUT,
        )

        all_results = finding_results + tool_results
        if not all_results:
            return ""

        # Sort by score
        all_results.sort(key=lambda r: r.score, reverse=True)

        lines: List[str] = []
        total_chars = 0

        for r in all_results:
            ts = r.metadata.get("timestamp", 0)
            ts_str = ""
            if ts:
                import datetime
                ts_str = f" | {datetime.datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%d')}"

            entry = f"[{r.doc_type.upper()}{ts_str} | relevance: {r.score:.0%}]\n{r.text}"
            if total_chars + len(entry) > max_chars:
                break
            lines.append(entry)
            total_chars += len(entry)

        if not lines:
            return ""

        return (
            f"[PRIOR INTELLIGENCE — Past data for target: {target}]\n"
            + "\n\n---\n\n".join(lines)
            + "\n[END PRIOR INTELLIGENCE]"
        )

    # ── Management ───────────────────────────────────────────────────────

    def clear(self, doc_type: Optional[str] = None) -> int:
        """Clear documents from memory.

        Args:
            doc_type: If given, only clear documents of this type.
                      If None, clear everything.

        Returns:
            Number of documents removed.
        """
        if not self._available:
            return 0

        try:
            if doc_type:
                # Get IDs of matching documents
                results = self._collection.get(
                    where={"doc_type": doc_type},
                )
                ids = results.get("ids", [])
                if ids:
                    self._collection.delete(ids=ids)
                return len(ids)
            else:
                count = self._collection.count()
                # Delete and recreate collection
                self._client.delete_collection(self._collection_name)
                self._collection = self._client.get_or_create_collection(
                    name=self._collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                return int(count)
        except Exception as exc:
            logger.warning("RAG clear failed: %s", exc)
            return 0

    def stats(self) -> Dict[str, Any]:
        """Return collection statistics."""
        if not self._available:
            return {
                "available": False,
                "total_documents": 0,
                "persist_dir": str(self._persist_dir),
            }

        total = self._collection.count()

        # Count by doc_type
        by_type: Dict[str, int] = {}
        for dtype in [DOC_CONVERSATION, DOC_FINDING, DOC_TOOL_OUTPUT, DOC_KNOWLEDGE]:
            try:
                result = self._collection.get(
                    where={"doc_type": dtype},
                    limit=1,
                    include=[],
                )
                # get() returns all matching IDs; count them
                by_type[dtype] = len(result.get("ids", []))
            except Exception:
                by_type[dtype] = 0

        # Count by type more accurately if total is reasonable
        if total <= 10000:
            try:
                for dtype in [DOC_CONVERSATION, DOC_FINDING, DOC_TOOL_OUTPUT, DOC_KNOWLEDGE]:
                    result = self._collection.get(
                        where={"doc_type": dtype},
                        include=[],
                    )
                    by_type[dtype] = len(result.get("ids", []))
            except Exception:
                pass

        # Disk size
        disk_bytes = 0
        if self._persist_dir.exists():
            for f in self._persist_dir.rglob("*"):
                if f.is_file():
                    disk_bytes += f.stat().st_size

        return {
            "available": True,
            "total_documents": total,
            "by_type": by_type,
            "persist_dir": str(self._persist_dir),
            "disk_size_mb": round(disk_bytes / (1024 * 1024), 2),
            "collection_name": self._collection_name,
        }

    def import_session(self, session_data: Dict[str, Any]) -> int:
        """Import a JSON session into the RAG memory.

        Args:
            session_data: A session dict as returned by ``MemoryManager.load_session()``.

        Returns:
            Number of chunks stored.
        """
        if not self._available:
            return 0

        session_id = session_data.get("id", "unknown")
        mode = session_data.get("mode", "chat")
        target = session_data.get("target", "")
        total_stored = 0

        # Import conversation messages
        for msg in session_data.get("messages", []):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role and content:
                total_stored += self.store_conversation(
                    role=role,
                    content=content,
                    session_id=session_id,
                    mode=mode,
                    target=target,
                )

        # Import findings (agent sessions)
        for finding in session_data.get("findings", []):
            if isinstance(finding, dict):
                finding["target"] = finding.get("target", target)
                total_stored += self.store_finding(finding)

        return total_stored


# ── Module-level singleton ───────────────────────────────────────────────────

_rag_instance: Optional[RAGMemory] = None


def get_rag_memory() -> RAGMemory:
    """Get or create the global RAG memory instance."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGMemory()
    return _rag_instance


def reset_rag_memory() -> None:
    """Reset the global RAG memory instance."""
    global _rag_instance
    _rag_instance = None
