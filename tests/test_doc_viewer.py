from pathlib import Path

import pytest

from policy_coherence_investigator.interfaces.doc_viewer import (
    load_markdown,
    render_markdown,
    resolve_media_path,
)


def test_renderer_keeps_native_details_and_renders_relative_images() -> None:
    page = render_markdown(
        "# Notes\n\n<details>\n<summary><strong>Learning</strong></summary>\n\n"
        "A ![sketch](images/idea.png) and **decision**.\n\n</details>"
    )

    assert "<details>" in page
    assert "<summary><strong>Learning</strong></summary>" in page
    assert '<img src="/media/images/idea.png" alt="sketch">' in page
    assert "<strong>decision</strong>" in page


def test_renderer_forces_every_details_section_closed() -> None:
    page = render_markdown(
        "<details open>\n<summary>Always start closed</summary>\n\nBody.\n\n</details>"
    )

    assert "<details>" in page
    assert "<details open>" not in page


def test_renderer_leaves_remote_images_and_links_untouched() -> None:
    page = render_markdown(
        "![remote](https://example.com/pic.png) and [site](https://example.com)"
    )

    assert '<img src="https://example.com/pic.png" alt="remote">' in page
    assert '<a href="https://example.com" target="_blank" rel="noreferrer">site</a>' in page


def test_renderer_escapes_non_supported_html() -> None:
    page = render_markdown("<script>alert('no')</script>")

    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_renderer_strips_trailing_inline_comments() -> None:
    page = render_markdown("Uppgiftsinstruktioner <!-- Väldigt öppna! -->")

    assert "Väldigt öppna" not in page
    assert "<p>Uppgiftsinstruktioner</p>" in page


def test_renderer_strips_standalone_comment_lines() -> None:
    page = render_markdown("# Heading\n\n<!-- Syfte: redovisa tankeprocess -->\n\nBody.")

    assert "Syfte" not in page


def test_renderer_keeps_comment_markers_literal_inside_code_blocks() -> None:
    page = render_markdown("```\n<!-- not a comment here -->\n```")

    assert "&lt;!-- not a comment here --&gt;" in page


def test_renderer_nests_list_items_by_indentation() -> None:
    page = render_markdown("- parent\n    - child\n    - child two\n- parent two")

    assert page == (
        "<ul>\n<li>parent</li>\n<ul>\n<li>child</li>\n<li>child two</li>\n"
        "</ul>\n<li>parent two</li>\n</ul>"
    )


def test_renderer_closes_nested_lists_when_returning_to_a_shallower_level() -> None:
    page = render_markdown("- a\n    - b\n        - c\n- d")

    assert page == (
        "<ul>\n<li>a</li>\n<ul>\n<li>b</li>\n<ul>\n<li>c</li>\n</ul>\n</ul>\n"
        "<li>d</li>\n</ul>"
    )


def test_load_markdown_reports_a_clear_error_for_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        load_markdown(tmp_path / "missing.md")


def test_resolve_media_path_serves_an_image_next_to_the_markdown_file(tmp_path: Path) -> None:
    markdown_path = tmp_path / "notes.md"
    markdown_path.write_text("# Notes", encoding="utf-8")
    image_path = tmp_path / "images" / "idea.png"
    image_path.parent.mkdir()
    image_path.write_bytes(b"small image")

    resolved = resolve_media_path(markdown_path, "images/idea.png")

    assert resolved == image_path


def test_resolve_media_path_rejects_traversal_outside_the_markdown_directory(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.png"
    secret.write_bytes(b"nope")
    inside = tmp_path / "inside"
    inside.mkdir()
    markdown_path = inside / "notes.md"
    markdown_path.write_text("# Notes", encoding="utf-8")

    assert resolve_media_path(markdown_path, "../outside/secret.png") is None


def test_resolve_media_path_rejects_unsupported_extensions(tmp_path: Path) -> None:
    markdown_path = tmp_path / "notes.md"
    markdown_path.write_text("# Notes", encoding="utf-8")
    other_file = tmp_path / "notes.txt"
    other_file.write_text("not an image", encoding="utf-8")

    assert resolve_media_path(markdown_path, "notes.txt") is None


def test_resolve_media_path_rejects_a_missing_file(tmp_path: Path) -> None:
    markdown_path = tmp_path / "notes.md"
    markdown_path.write_text("# Notes", encoding="utf-8")

    assert resolve_media_path(markdown_path, "images/missing.png") is None
