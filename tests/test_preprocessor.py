import pytest
from pipeline.preprocessor import preprocess


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_string_returns_empty_list():
    assert preprocess("") == []


def test_whitespace_only_returns_empty_list():
    assert preprocess("   \n\n   ") == []


def test_single_paragraph_no_markdown():
    assert preprocess("Just plain text.") == ["Just plain text."]


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

def test_strips_yaml_frontmatter():
    text = "---\ntitle: Test\ndate: 2024-01-01\n---\n\nHello world."
    assert preprocess(text) == ["Hello world."]


def test_frontmatter_only_returns_empty():
    assert preprocess("---\ntitle: Test\n---\n") == []


def test_body_after_frontmatter_preserved():
    text = "---\nauthor: Alice\n---\n\nFirst paragraph.\n\nSecond paragraph."
    result = preprocess(text)
    assert "First paragraph." in result
    assert "Second paragraph." in result


# ---------------------------------------------------------------------------
# Code blocks
# ---------------------------------------------------------------------------

def test_strips_fenced_code_block():
    text = "Before.\n\n```python\nprint('hello')\n```\n\nAfter."
    result = preprocess(text)
    assert "print" not in " ".join(result)
    assert "Before." in result
    assert "After." in result


def test_strips_tilde_code_block():
    text = "Before.\n\n~~~\nsome_code()\n~~~\n\nAfter."
    result = preprocess(text)
    assert "some_code" not in " ".join(result)
    assert "Before." in result


def test_strips_indented_code_block():
    text = "Before.\n\n    indented_code = True\n\nAfter."
    result = preprocess(text)
    assert "indented_code" not in " ".join(result)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def test_strips_image_entirely():
    text = "Look: ![A dog](http://example.com/dog.jpg) — nice photo."
    result = preprocess(text)
    assert "![" not in result[0]
    assert "dog.jpg" not in result[0]


def test_strips_image_alt_text_too():
    text = "Caption: ![descriptive alt text](image.png)"
    result = preprocess(text)
    assert "alt text" not in " ".join(result)


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------

def test_keeps_link_text_drops_url():
    text = "Visit [the homepage](https://example.com) for details."
    result = preprocess(text)
    assert "the homepage" in result[0]
    assert "example.com" not in result[0]


def test_strips_bare_http_url():
    text = "Read more at https://example.com for context."
    result = preprocess(text)
    assert "https" not in result[0]
    assert "Read more at" in result[0]


def test_strips_angle_bracket_url():
    text = "See <https://example.com> for reference."
    result = preprocess(text)
    assert "example.com" not in result[0]


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------

def test_strips_h1_marker_keeps_text():
    text = "# My Great Heading\n\nBody text."
    result = preprocess(text)
    assert "My Great Heading" in result
    assert "#" not in " ".join(result)


def test_strips_h3_marker_keeps_text():
    text = "### Sub Section\n\nBody."
    result = preprocess(text)
    assert "Sub Section" in result
    assert "###" not in " ".join(result)


# ---------------------------------------------------------------------------
# Formatting markers
# ---------------------------------------------------------------------------

def test_strips_bold_asterisks():
    assert preprocess("This is **bold** text.") == ["This is bold text."]


def test_strips_bold_underscores():
    assert preprocess("This is __bold__ text.") == ["This is bold text."]


def test_strips_italic_asterisk():
    assert preprocess("This is *italic* text.") == ["This is italic text."]


def test_strips_italic_underscore():
    assert preprocess("This is _italic_ text.") == ["This is italic text."]


def test_strips_bold_italic():
    assert preprocess("This is ***bold italic*** text.") == ["This is bold italic text."]


def test_strips_strikethrough():
    assert preprocess("This is ~~deleted~~ text.") == ["This is deleted text."]


# ---------------------------------------------------------------------------
# Inline code
# ---------------------------------------------------------------------------

def test_strips_inline_code():
    result = preprocess("Call the `my_function()` method.")
    assert "`" not in result[0]
    assert "my_function" not in result[0]
    assert "Call the" in result[0]
    assert "method." in result[0]


# ---------------------------------------------------------------------------
# Blockquotes
# ---------------------------------------------------------------------------

def test_strips_blockquote_marker():
    text = "> This is a quote.\n> It continues here."
    result = preprocess(text)
    assert ">" not in " ".join(result)
    assert "This is a quote." in result[0]


def test_multiline_blockquote_collapses_to_paragraph():
    text = "> Line one.\n> Line two."
    result = preprocess(text)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Horizontal rules
# ---------------------------------------------------------------------------

def test_strips_horizontal_rule_dashes():
    text = "Above.\n\n---\n\nBelow."
    result = preprocess(text)
    assert "Above." in result
    assert "Below." in result
    assert "---" not in " ".join(result)


def test_strips_horizontal_rule_asterisks():
    text = "Above.\n\n***\n\nBelow."
    result = preprocess(text)
    assert "***" not in " ".join(result)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def test_strips_html_tags_keeps_content():
    text = "Some <em>emphasized</em> text."
    result = preprocess(text)
    assert "<em>" not in result[0]
    assert "</em>" not in result[0]
    assert "emphasized" in result[0]


def test_strips_self_closing_html():
    text = "Line one.<br>Line two."
    result = preprocess(text)
    assert "<br>" not in result[0]


# ---------------------------------------------------------------------------
# Paragraph splitting
# ---------------------------------------------------------------------------

def test_splits_on_double_newline():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    result = preprocess(text)
    assert len(result) == 3
    assert result[0] == "First paragraph."
    assert result[1] == "Second paragraph."
    assert result[2] == "Third paragraph."


def test_collapses_internal_newlines_to_space():
    text = "First line\nsecond line\nthird line."
    result = preprocess(text)
    assert len(result) == 1
    assert result[0] == "First line second line third line."


def test_three_plus_blank_lines_treated_as_one_paragraph_break():
    text = "First.\n\n\n\n\n\nSecond."
    result = preprocess(text)
    assert len(result) == 2


def test_filters_empty_paragraphs():
    text = "\n\nActual content.\n\n"
    result = preprocess(text)
    assert result == ["Actual content."]


# ---------------------------------------------------------------------------
# Combined / real-world
# ---------------------------------------------------------------------------

def test_full_mixed_markdown():
    text = (
        "---\ntitle: My Post\n---\n\n"
        "# Introduction\n\n"
        "This is **bold** and *italic*. Visit [the site](https://example.com).\n\n"
        "```python\ncode_here()\n```\n\n"
        "Final paragraph."
    )
    result = preprocess(text)
    joined = " ".join(result)
    assert "Introduction" in result
    assert "**" not in joined
    assert "example.com" not in joined
    assert "code_here" not in joined
    assert "Final paragraph." in result
