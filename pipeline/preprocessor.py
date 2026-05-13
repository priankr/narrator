import re


def preprocess(text: str) -> list[str]:
    """Convert raw Markdown to a list of plain-text paragraphs ready for TTS."""
    text = _strip_frontmatter(text)
    text = _strip_code_blocks(text)
    text = _strip_images(text)
    text = _strip_links(text)
    text = _strip_urls(text)
    text = _strip_heading_markers(text)
    text = _strip_formatting_markers(text)
    text = _strip_inline_code(text)
    text = _strip_blockquote_markers(text)
    text = _strip_horizontal_rules(text)
    text = _strip_html_tags(text)
    text = _normalize_whitespace(text)
    return _split_paragraphs(text)


# --- private helpers ---------------------------------------------------------

def _strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)


def _strip_code_blocks(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.DOTALL)
    # Indented code blocks (4-space or tab-indented lines)
    text = re.sub(r"^( {4}|\t).+$", "", text, flags=re.MULTILINE)
    return text


def _strip_images(text: str) -> str:
    return re.sub(r"!\[.*?\]\(.*?\)", "", text)


def _strip_links(text: str) -> str:
    # Keep link text, drop URL: [text](url) → text
    return re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)


def _strip_urls(text: str) -> str:
    # Bare URLs (http/https)
    text = re.sub(r"https?://\S+", "", text)
    # Angle-bracket URLs: <https://...>
    text = re.sub(r"<https?://[^>]+>", "", text)
    return text


def _strip_heading_markers(text: str) -> str:
    # Remove # markers but keep the heading text so it is read aloud
    return re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)


def _strip_formatting_markers(text: str) -> str:
    # Bold+italic: ***text*** or ___text___
    text = re.sub(r"\*{3}(.+?)\*{3}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"_{3}(.+?)_{3}", r"\1", text, flags=re.DOTALL)
    # Bold: **text** or __text__
    text = re.sub(r"\*{2}(.+?)\*{2}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"_{2}(.+?)_{2}", r"\1", text, flags=re.DOTALL)
    # Italic: *text* or _text_
    text = re.sub(r"\*(.+?)\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"_(.+?)_", r"\1", text, flags=re.DOTALL)
    # Strikethrough: ~~text~~
    text = re.sub(r"~~(.+?)~~", r"\1", text, flags=re.DOTALL)
    return text


def _strip_inline_code(text: str) -> str:
    return re.sub(r"`[^`\n]+`", "", text)


def _strip_blockquote_markers(text: str) -> str:
    return re.sub(r"^>\s?", "", text, flags=re.MULTILINE)


def _strip_horizontal_rules(text: str) -> str:
    return re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)


def _strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _normalize_whitespace(text: str) -> str:
    # Collapse 3+ blank lines to 2 (one paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = text.split("\n\n")
    # Flatten any remaining internal newlines within a paragraph to a space
    paragraphs = [p.replace("\n", " ").strip() for p in paragraphs]
    return [p for p in paragraphs if p]
