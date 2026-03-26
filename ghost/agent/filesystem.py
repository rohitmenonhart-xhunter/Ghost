"""File System Operations — Read, write, manage files and downloads.

Ghost can:
- List directory contents
- Read file contents
- Write/create files
- Move, copy, rename files
- Monitor downloads folder
- Open files in appropriate apps
"""

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

SYSTEM = platform.system()

# Default downloads directory
DOWNLOADS = {
    "Darwin": str(Path.home() / "Downloads"),
    "Linux": str(Path.home() / "Downloads"),
    "Windows": str(Path.home() / "Downloads"),
}


class FileSystem:
    """File system operations for Ghost."""

    def __init__(self, downloads_dir: Optional[str] = None):
        self.downloads_dir = Path(downloads_dir or DOWNLOADS.get(SYSTEM, str(Path.home() / "Downloads")))

    # ── Read ─────────────────────────────────────────────────────

    def list_dir(self, path: str = ".", pattern: str = "*") -> list[dict]:
        """List directory contents."""
        p = Path(path).expanduser()
        if not p.exists():
            return []

        items = []
        for item in sorted(p.glob(pattern)):
            items.append({
                "name": item.name,
                "path": str(item),
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0,
                "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(item.stat().st_mtime)),
            })
        return items

    def read_file(self, path: str, max_chars: int = 10000) -> str:
        """Read a text file's contents."""
        p = Path(path).expanduser()
        if not p.exists():
            return f"File not found: {path}"
        if not p.is_file():
            return f"Not a file: {path}"
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            if len(text) > max_chars:
                return text[:max_chars] + f"\n... (truncated, {len(text)} total chars)"
            return text
        except Exception as e:
            return f"Error reading file: {e}"

    def file_info(self, path: str) -> dict:
        """Get file metadata."""
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"Not found: {path}"}
        stat = p.stat()
        return {
            "name": p.name,
            "path": str(p),
            "size": stat.st_size,
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
            "is_dir": p.is_dir(),
            "extension": p.suffix,
        }

    # ── Write ────────────────────────────────────────────────────

    def write_file(self, path: str, content: str) -> bool:
        """Write text to a file. Creates parent dirs if needed."""
        try:
            p = Path(path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    def append_file(self, path: str, content: str) -> bool:
        """Append text to a file."""
        try:
            p = Path(path).expanduser()
            with open(p, "a", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False

    # ── Move / Copy / Delete ─────────────────────────────────────

    def move(self, src: str, dst: str) -> bool:
        """Move a file or directory."""
        try:
            shutil.move(str(Path(src).expanduser()), str(Path(dst).expanduser()))
            return True
        except Exception:
            return False

    def copy(self, src: str, dst: str) -> bool:
        """Copy a file or directory."""
        try:
            s = Path(src).expanduser()
            d = Path(dst).expanduser()
            if s.is_dir():
                shutil.copytree(str(s), str(d))
            else:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(s), str(d))
            return True
        except Exception:
            return False

    def rename(self, path: str, new_name: str) -> bool:
        """Rename a file or directory."""
        try:
            p = Path(path).expanduser()
            p.rename(p.parent / new_name)
            return True
        except Exception:
            return False

    def delete(self, path: str) -> bool:
        """Delete a file or empty directory. USE WITH CAUTION."""
        try:
            p = Path(path).expanduser()
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                p.rmdir()  # only empty dirs
            return True
        except Exception:
            return False

    def mkdir(self, path: str) -> bool:
        """Create a directory (and parents)."""
        try:
            Path(path).expanduser().mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    # ── Downloads ────────────────────────────────────────────────

    def recent_downloads(self, count: int = 10) -> list[dict]:
        """Get recent files in downloads folder."""
        items = self.list_dir(str(self.downloads_dir))
        # Sort by modified time, most recent first
        items.sort(key=lambda x: x["modified"], reverse=True)
        return items[:count]

    def wait_for_download(self, filename_contains: str = "", timeout: float = 60) -> Optional[str]:
        """Wait for a new file to appear in downloads."""
        before = set(self.downloads_dir.iterdir())
        start = time.time()

        while time.time() - start < timeout:
            current = set(self.downloads_dir.iterdir())
            new_files = current - before

            for f in new_files:
                if not f.name.endswith((".crdownload", ".part", ".tmp")):
                    if not filename_contains or filename_contains.lower() in f.name.lower():
                        return str(f)

            time.sleep(1)

        return None

    # ── Open ─────────────────────────────────────────────────────

    def open_file(self, path: str, app: Optional[str] = None):
        """Open a file with the default or specified application."""
        p = str(Path(path).expanduser())
        if SYSTEM == "Darwin":
            cmd = ["open", p] if not app else ["open", "-a", app, p]
        elif SYSTEM == "Linux":
            cmd = ["xdg-open", p] if not app else [app, p]
        elif SYSTEM == "Windows":
            cmd = ["start", p] if not app else ["start", app, p]
        else:
            return

        subprocess.run(cmd, check=False)

    # ── Search ───────────────────────────────────────────────────

    def find_files(self, directory: str, pattern: str, max_results: int = 20) -> list[str]:
        """Find files matching a glob pattern recursively."""
        results = []
        for f in Path(directory).expanduser().rglob(pattern):
            results.append(str(f))
            if len(results) >= max_results:
                break
        return results

    def format_for_llm(self, path: str = ".") -> str:
        """Format directory listing for AI context."""
        items = self.list_dir(path)
        if not items:
            return f"Directory empty or not found: {path}"

        lines = [f"DIRECTORY: {Path(path).resolve()} ({len(items)} items)"]
        for item in items[:30]:
            icon = "📁" if item["is_dir"] else "📄"
            size = f" ({item['size']}B)" if not item["is_dir"] else ""
            lines.append(f"  {icon} {item['name']}{size}")
        return "\n".join(lines)
