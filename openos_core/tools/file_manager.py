"""
OpenOS Smart File Manager Tool.

Auto-organize files, detect duplicates, search files, and suggest cleanup.
"""

from __future__ import annotations

import hashlib
import shutil
from collections import defaultdict
from pathlib import Path

from openos_core.tools.base import BaseTool, tool_function

# File type categories for auto-organization
FILE_CATEGORIES = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md", ".tex", ".epub"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus"},
    "Archives": {".zip", ".tar", ".gz", ".bz2", ".xz", ".rar", ".7z", ".deb"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".go", ".rs", ".sh"},
    "Data": {".csv", ".json", ".xml", ".yaml", ".yml", ".sql", ".db", ".sqlite"},
    "Executables": {".AppImage", ".bin", ".run"},
}


class FileManagerTool(BaseTool):
    """Smart file management: organize, search, deduplicate, cleanup."""

    @property
    def name(self) -> str:
        return "file_manager"

    @property
    def description(self) -> str:
        return "Smart file management — organize, search, deduplicate, and cleanup files"

    @tool_function(
        description="Organize files in a directory by sorting them into categorized subfolders (Documents, Images, Videos, etc.)",
        parameters={
            "path": {"type": "string", "description": "Directory path to organize (e.g., ~/Downloads)"},
            "dry_run": {"type": "boolean", "description": "If true, show plan without moving files", "optional": True},
        },
    )
    def organize_directory(self, path: str, dry_run: bool = False) -> str:
        target = Path(path).expanduser().resolve()
        if not target.is_dir():
            return f"Error: '{path}' is not a directory"

        moves = []
        for item in target.iterdir():
            if item.is_dir() or item.name.startswith("."):
                continue
            ext = item.suffix.lower()
            category = "Other"
            for cat, extensions in FILE_CATEGORIES.items():
                if ext in extensions:
                    category = cat
                    break
            dest_dir = target / category
            moves.append((item, dest_dir / item.name))

        if not moves:
            return "Directory is already clean — no files to organize."

        if dry_run:
            lines = [f"Plan for {target} ({len(moves)} files):"]
            by_cat = defaultdict(list)
            for src, dst in moves:
                by_cat[dst.parent.name].append(src.name)
            for cat, files in sorted(by_cat.items()):
                lines.append(f"\n📁 {cat}/ ({len(files)} files)")
                for f in files[:5]:
                    lines.append(f"  └─ {f}")
                if len(files) > 5:
                    lines.append(f"  └─ ... and {len(files)-5} more")
            return "\n".join(lines)

        moved = 0
        for src, dst in moves:
            dst.parent.mkdir(exist_ok=True)
            shutil.move(str(src), str(dst))
            moved += 1

        return f"✅ Organized {moved} files into categorized folders in {target}"

    @tool_function(
        description="Find duplicate files in a directory using content hashing",
        parameters={
            "path": {"type": "string", "description": "Directory to scan for duplicates"},
        },
    )
    def find_duplicates(self, path: str) -> str:
        target = Path(path).expanduser().resolve()
        if not target.is_dir():
            return f"Error: '{path}' is not a directory"

        hashes: dict[str, list[str]] = defaultdict(list)
        for item in target.rglob("*"):
            if item.is_file() and item.stat().st_size > 0:
                try:
                    h = hashlib.md5(item.read_bytes()).hexdigest()
                    hashes[h].append(str(item))
                except (PermissionError, OSError):
                    continue

        dupes = {h: paths for h, paths in hashes.items() if len(paths) > 1}
        if not dupes:
            return "No duplicates found."

        total_wasted = 0
        lines = [f"Found {len(dupes)} sets of duplicates:\n"]
        for i, (h, paths) in enumerate(dupes.items(), 1):
            size = Path(paths[0]).stat().st_size
            wasted = size * (len(paths) - 1)
            total_wasted += wasted
            lines.append(f"Set {i} ({_human_size(size)} each):")
            for p in paths:
                lines.append(f"  • {p}")

        lines.append(f"\n💾 Total wasted space: {_human_size(total_wasted)}")
        return "\n".join(lines)

    @tool_function(
        description="Search for files by name pattern in a directory",
        parameters={
            "query": {"type": "string", "description": "Search term (filename pattern)"},
            "path": {"type": "string", "description": "Directory to search in", "optional": True},
        },
    )
    def search_files(self, query: str, path: str = "~") -> str:
        target = Path(path).expanduser().resolve()
        results: list[str] = []
        for item in target.rglob(f"*{query}*"):
            if len(results) >= 20:
                break
            try:
                size = _human_size(item.stat().st_size) if item.is_file() else "DIR"
                results.append(f"  {size:>8}  {item}")
            except (PermissionError, OSError):
                continue

        if not results:
            return f"No files matching '{query}' found in {target}"
        return f"Found {len(results)} results:\n" + "\n".join(results)

    @tool_function(
        description="Analyze a directory and suggest cleanup actions for large, old, or temporary files",
        parameters={
            "path": {"type": "string", "description": "Directory to analyze", "optional": True},
        },
    )
    def suggest_cleanup(self, path: str = "~") -> str:
        target = Path(path).expanduser().resolve()
        large_files = []
        total_size = 0

        for item in target.rglob("*"):
            if not item.is_file():
                continue
            try:
                size = item.stat().st_size
                total_size += size
                if size > 100 * 1024 * 1024:  # > 100MB
                    large_files.append((item, size))
            except (PermissionError, OSError):
                continue

        large_files.sort(key=lambda x: x[1], reverse=True)

        lines = [f"📊 Directory Analysis: {target}", f"Total size: {_human_size(total_size)}\n"]

        if large_files:
            lines.append(f"🗂️ Large files (>100MB): {len(large_files)}")
            for f, s in large_files[:10]:
                lines.append(f"  {_human_size(s):>10}  {f.name}")

        # Check common cleanup targets
        cache_dirs = [".cache", "__pycache__", "node_modules", ".tmp"]
        for cd in cache_dirs:
            cache_path = target / cd
            if cache_path.is_dir():
                cache_size = sum(f.stat().st_size for f in cache_path.rglob("*") if f.is_file())
                if cache_size > 1024 * 1024:
                    lines.append(f"\n🧹 {cd}/: {_human_size(cache_size)} (safe to clean)")

        return "\n".join(lines)


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size."""
    val = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024:
            return f"{val:.1f}{unit}"
        val /= 1024
    return f"{val:.1f}PB"
