"""Open an idealine:// link in IntelliJ: idealine:///<absolute path>:<line>  ->  idea://open?file=<path>&line=<line>

idea:// links break in VS Code's markdown preview (it percent-encodes their '=' and '&'), and an http link opens a
browser tab. This link has no query, and whatever VS Code encodes is decoded here, so it opens straight in IntelliJ.
"""
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote

SCHEME_PREFIX = "idealine://"
CODE_ROOT = Path.home() / "repos"


def idea_url_for(idealine_url: str) -> Optional[str]:
    """The idea:// URL for an existing file under CODE_ROOT, or None."""
    decoded = unquote(idealine_url)
    if not decoded.startswith(SCHEME_PREFIX):
        return None
    file_and_line = decoded[len(SCHEME_PREFIX):]
    file_part, _, line_part = file_and_line.rpartition(":")
    if not line_part.isdigit():
        file_part, line_part = file_and_line, "1"
    code_file = Path(file_part).resolve()
    if CODE_ROOT.resolve() not in code_file.parents or not code_file.is_file():
        return None
    return f"idea://open?file={quote(str(code_file))}&line={line_part}"


def main(idealine_url: str) -> int:
    idea_url = idea_url_for(idealine_url)
    if idea_url is None:
        print(f"not a code file under {CODE_ROOT}: {idealine_url}", file=sys.stderr)
        return 1
    return subprocess.run(["open", idea_url], check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
