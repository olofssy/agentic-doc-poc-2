# ruff: noqa: E501
"""Read-only local renderer for a single human-authored Markdown file.

Point it at any Markdown file to view it with images and native
``<details>``/``<summary>`` collapsible sections, so long documents can stay
skimmable instead of dumping everything at once. Every section renders
collapsed, regardless of an ``open`` attribute in the source, so a freshly
loaded page never dumps everything at once. Edit the file in your own
editor; the page polls for changes and reloads on save. This has no
dependency on the investigator, evaluation, or case data and must stay that
way.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Final
from urllib.parse import unquote, urlparse

IMAGE_CONTENT_TYPES: Final[dict[str, str]] = {
    ".gif": "image/gif",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


def load_markdown(path: Path) -> str:
    """Read the Markdown file, failing clearly when it is missing."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        msg = f"Markdown file does not exist: {path}"
        raise ValueError(msg) from error


def render_markdown(markdown: str) -> str:
    """Render the small, portable Markdown subset used by the doc viewer.

    Native ``details`` and ``summary`` tags intentionally pass through so
    section collapse stays browser-native, but every ``details`` element is
    forced closed on render, even if the source says ``<details open>`` -
    a freshly loaded page should never dump everything at once. All other
    user-provided text is escaped before HTML is emitted.

    HTML comments (``<!-- ... -->``) are stripped wherever they appear -
    on their own line or trailing other content - except inside fenced
    code blocks, where they're left as literal text. List items nest
    based on leading indentation, so a bullet indented further than its
    parent renders inside a nested ``<ul>``.
    """
    rendered: list[str] = []
    paragraph: list[str] = []
    in_code_block = False
    code_lines: list[str] = []
    list_indents: list[int] = []

    def flush_paragraph() -> None:
        if paragraph:
            rendered.append(f"<p>{_render_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        while list_indents:
            rendered.append("</ul>")
            list_indents.pop()

    for raw_line in markdown.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            if in_code_block:
                rendered.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
            in_code_block = not in_code_block
            continue
        if in_code_block:
            code_lines.append(raw_line)
            continue
        line = re.sub(r"<!--.*?-->", "", raw_line)
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            continue
        if stripped in {"<details>", "<details open>", "</details>"}:
            flush_paragraph()
            close_list()
            rendered.append("</details>" if stripped == "</details>" else "<details>")
            continue
        if stripped.startswith("<summary>") and stripped.endswith("</summary>"):
            flush_paragraph()
            close_list()
            rendered.append(_render_summary(stripped))
            continue
        if match := re.fullmatch(r"(#{1,3})\s+(.+)", stripped):
            flush_paragraph()
            close_list()
            level = len(match.group(1))
            rendered.append(f"<h{level}>{_render_inline(match.group(2))}</h{level}>")
            continue
        if match := re.match(r"^(\s*)[-*]\s+(.+)$", line):
            flush_paragraph()
            indent = len(match.group(1).expandtabs(4))
            while list_indents and indent < list_indents[-1]:
                rendered.append("</ul>")
                list_indents.pop()
            if not list_indents or indent > list_indents[-1]:
                rendered.append("<ul>")
                list_indents.append(indent)
            rendered.append(f"<li>{_render_inline(match.group(2))}</li>")
            continue
        close_list()
        paragraph.append(stripped)

    if in_code_block:
        rendered.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    flush_paragraph()
    close_list()
    return "\n".join(rendered)


def _render_summary(summary: str) -> str:
    """Allow harmless emphasis inside a native summary element."""
    content = summary.removeprefix("<summary>").removesuffix("</summary>")
    return f"<summary>{_render_inline(content, allow_strong=True)}</summary>"


def _render_inline(text: str, *, allow_strong: bool = False) -> str:
    """Escape text then render standard image, link, emphasis, and strong-markup forms."""
    escaped = html.escape(text)
    if allow_strong:
        escaped = re.sub(r"&lt;strong&gt;(.*?)&lt;/strong&gt;", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r"!\[([^\]]*)\]\((?!https?://)([^\s)]+)\)",
        r'<img src="/media/\2" alt="\1">',
        escaped,
    )
    escaped = re.sub(
        r"!\[([^\]]*)\]\((https?://[^\s)]+)\)",
        r'<img src="\2" alt="\1">',
        escaped,
    )
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        r'<a href="\2" target="_blank" rel="noreferrer">\1</a>',
        escaped,
    )
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped


def resolve_media_path(markdown_path: Path, relative: str) -> Path | None:
    """Resolve an image reference to a file under the Markdown file's directory.

    Returns ``None`` for traversal outside that directory, unsupported
    extensions, or a missing file, so the caller can answer with a plain 404.
    """
    base_directory = markdown_path.resolve().parent
    candidate = (base_directory / unquote(relative)).resolve()
    if candidate.suffix.lower() not in IMAGE_CONTENT_TYPES:
        return None
    if not candidate.is_relative_to(base_directory):
        return None
    if not candidate.is_file():
        return None
    return candidate


def make_request_handler(markdown_path: Path) -> type[BaseHTTPRequestHandler]:
    """Create the local viewer handler closed over one explicitly selected Markdown file."""

    class DocViewerRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(_render_page(load_markdown(markdown_path)))
                return
            if parsed.path == "/api/mtime":
                self._send_json({"mtime": markdown_path.stat().st_mtime})
                return
            if parsed.path.startswith("/media/"):
                self._serve_media(parsed.path.removeprefix("/media/"))
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def _serve_media(self, relative: str) -> None:
            resolved = resolve_media_path(markdown_path, relative)
            if resolved is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_type = IMAGE_CONTENT_TYPES[resolved.suffix.lower()]
            body = resolved.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, page: str) -> None:
            body = page.encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, payload: dict[str, float]) -> None:
            body = json.dumps(payload).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            """Keep the local viewer quiet except for its startup message."""

    return DocViewerRequestHandler


def _render_page(markdown: str) -> str:
    """Render the read-only viewer shell with the current Markdown already inlined."""
    encoded_preview = json.dumps(render_markdown(markdown))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Doc viewer</title><style>
:root {{ color-scheme: light; font-family: ui-sans-serif, system-ui, sans-serif; color: #17232b; background: #f4f7f8; }}
body {{ margin: 0; }} article {{ max-width: 770px; margin: 0 auto; padding: 40px clamp(20px, 5vw, 56px); line-height: 1.55; }}
article h1 {{ font-size: 2rem; }} article h2 {{ margin-top: 30px; }} article h3 {{ margin-top: 24px; }}
article details {{ margin: 12px 0; border: 1px solid #cedbe0; border-radius: 7px; background: white; overflow: hidden; }}
article summary {{ padding: 12px 15px; cursor: pointer; color: #c3cdd2; }} article details[open] summary {{ color: #17232b; }} article details > :not(summary) {{ margin-left: 15px; margin-right: 15px; }}
article img {{ max-width: 100%; height: auto; border-radius: 6px; }} article code {{ padding: .1em .3em; border-radius: 4px; background: #eaf0f2; }}
article pre {{ padding: 14px; overflow: auto; border-radius: 6px; background: #eaf0f2; }} article pre code {{ padding: 0; }} article a {{ color: #0d666c; }}
</style></head><body>
<article id="preview">{json.loads(encoded_preview)}</article>
<script>
let knownMtime = null;
async function pollForChanges() {{
  try {{
    const response = await fetch('/api/mtime');
    const {{ mtime }} = await response.json();
    if (knownMtime === null) {{ knownMtime = mtime; }}
    else if (mtime !== knownMtime) {{ location.reload(); }}
  }} catch (error) {{ /* server not reachable yet; keep polling */ }}
}}
setInterval(pollForChanges, 1000);
</script></body></html>"""


def main() -> None:
    """Start the read-only viewer without invoking a model or evaluation."""
    parser = argparse.ArgumentParser(description="Render a local Markdown file with collapsible sections.")
    parser.add_argument("path", type=Path, help="Markdown file to render.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to listen on.")
    parser.add_argument("--port", type=int, default=8768, help="TCP port to listen on.")
    args = parser.parse_args()

    markdown_path = args.path.resolve()
    if not markdown_path.is_file():
        raise SystemExit(f"Markdown file does not exist: {markdown_path}")

    server = ThreadingHTTPServer((args.host, args.port), make_request_handler(markdown_path))
    print(f"Doc viewer running at http://{args.host}:{args.port} (watching {markdown_path})")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDoc viewer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
