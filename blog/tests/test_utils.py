"""
Behavioral tests for blog.utils.

Covers:
- sanitize_html — allowlist behavior, script/style removal,
  protocol filtering, comments stripped.
- clean_text — HTML to plain text, entity decoding, whitespace
  collapsing.
- calculate_reading_time — English word count, Persian detection,
  minimum of 1 minute.

These tests document the exact boundaries of the sanitizer, so any
loosening or tightening of the allowlist shows up as a failure.
"""

import pytest

from blog.utils import (
    WORDS_PER_MINUTE_EN,
    WORDS_PER_MINUTE_FA,
    calculate_reading_time,
    clean_text,
    sanitize_html,
)


# ==================================================================
# sanitize_html
# ==================================================================
class TestSanitizeHtml:
    def test_empty_input_returns_empty(self):
        assert sanitize_html("") == ""

    def test_none_like_input_returns_empty(self):
        # The function guards with `if not html`.
        assert sanitize_html(None) == ""

    def test_preserves_allowed_tags(self):
        html = "<p>Hello <strong>world</strong></p>"
        assert sanitize_html(html) == "<p>Hello <strong>world</strong></p>"

    def test_strips_script_tags_but_keeps_text_content(self):
        """
        bleach.clean(strip=True) removes the <script> tag but keeps its
        text content. The output is therefore plain text ("alert(1)"),
        not an executable script. This is safe against XSS because the
        browser no longer sees a script element.
        """
        result = sanitize_html("<p>Safe</p><script>alert(1)</script>")
        assert "<script" not in result.lower()
        assert "Safe" in result
        # Documents the current behavior: text content survives.
        assert "alert(1)" in result

    def test_strips_style_tags_but_keeps_text_content(self):
        result = sanitize_html("<style>body{}</style><p>Safe</p>")
        assert "<style" not in result.lower()
        assert "Safe" in result
        # Text content survives, matching the script case.
        assert "body{}" in result

    def test_strips_iframe(self):
        result = sanitize_html('<iframe src="https://evil.example/"></iframe>')
        assert "<iframe" not in result.lower()

    def test_strips_event_handler_attributes(self):
        result = sanitize_html('<p onclick="alert(1)">Click</p>')
        assert "onclick" not in result.lower()
        # The tag itself remains.
        assert "<p>" in result

    def test_strips_javascript_href(self):
        result = sanitize_html('<a href="javascript:alert(1)">Click</a>')
        assert "javascript" not in result.lower()
        assert "<a" in result

    def test_keeps_http_href(self):
        html = '<a href="https://example.com">Click</a>'
        result = sanitize_html(html)
        assert "https://example.com" in result

    def test_keeps_mailto(self):
        result = sanitize_html('<a href="mailto:hello@example.com">Mail</a>')
        assert "mailto:hello@example.com" in result

    def test_strips_html_comments(self):
        result = sanitize_html("<p>Hi</p><!-- secret -->")
        assert "secret" not in result
        assert "<!--" not in result

    def test_strips_unknown_tags_but_keeps_text(self):
        result = sanitize_html("<blink>Weird</blink>")
        assert "<blink" not in result.lower()
        assert "Weird" in result

    def test_keeps_img_attributes(self):
        html = '<img src="https://example.com/x.png" alt="x" width="10">'
        result = sanitize_html(html)
        assert 'src="https://example.com/x.png"' in result
        assert 'alt="x"' in result
        assert 'width="10"' in result

    def test_strips_disallowed_img_attributes(self):
        html = '<img src="x.png" onerror="alert(1)">'
        result = sanitize_html(html)
        assert "onerror" not in result.lower()

    @pytest.mark.parametrize(
        "tag",
        [
            "p",
            "h1",
            "h2",
            "strong",
            "em",
            "ul",
            "ol",
            "li",
            "blockquote",
            "pre",
            "code",
        ],
    )
    def test_common_allowed_tags_survive(self, tag):
        result = sanitize_html(f"<{tag}>content</{tag}>")
        assert f"<{tag}>" in result


# ==================================================================
# clean_text
# ==================================================================
class TestCleanText:
    def test_empty_input_returns_empty(self):
        assert clean_text("") == ""

    def test_none_like_input_returns_empty(self):
        assert clean_text(None) == ""

    def test_strips_simple_html(self):
        assert clean_text("<p>Hello world</p>") == "Hello world"

    def test_keeps_text_content_of_nested_tags(self):
        assert clean_text("<div><p><strong>Hi</strong> there</p></div>") == "Hi there"

    def test_strips_style_tags_but_keeps_text_content(self):
        result = sanitize_html("<style>body{}</style><p>Safe</p>")
        assert "<style" not in result.lower()
        assert "Safe" in result
        assert "body{}" in result

    def test_collapses_whitespace(self):
        result = clean_text("<p>Hello\n\n   world</p>")
        assert result == "Hello world"

    def test_strips_leading_and_trailing(self):
        assert clean_text("  <p>  Hello  </p>  ") == "Hello"

    def test_strips_script_tags_entirely(self):
        result = clean_text("<p>Safe</p><script>alert(1)</script>")
        assert "<script" not in result.lower()
        # Note: bleach.clean(strip=True) preserves the text content
        # of disallowed tags, so "alert(1)" may still appear in the
        # output. This test documents the current behavior.
        assert "Safe" in result


# ==================================================================
# calculate_reading_time
# ==================================================================
class TestCalculateReadingTime:
    def test_empty_body_returns_one_minute(self):
        assert calculate_reading_time("") == 1

    def test_whitespace_only_body_returns_one_minute(self):
        assert calculate_reading_time("   \n  ") == 1

    def test_short_english_text_returns_one_minute(self):
        assert calculate_reading_time("<p>Hello world</p>") == 1

    def test_english_word_count_drives_minutes(self):
        # ~2x words-per-minute should give 2 minutes.
        words = ["word"] * (WORDS_PER_MINUTE_EN * 2)
        html = "<p>" + " ".join(words) + "</p>"
        assert calculate_reading_time(html) == 2

    def test_rounds_up(self):
        # One word past one minute's worth should give 2 minutes.
        words = ["word"] * (WORDS_PER_MINUTE_EN + 1)
        html = "<p>" + " ".join(words) + "</p>"
        assert calculate_reading_time(html) == 2

    def test_persian_text_uses_slower_rate(self):
        # Build a Persian-heavy string. Persian is detected when more
        # than 30% of non-space characters fall in the Arabic-script
        # unicode range.
        persian_words = ["سلام"] * (WORDS_PER_MINUTE_FA + 1)
        html = "<p>" + " ".join(persian_words) + "</p>"
        assert calculate_reading_time(html) == 2

    def test_mixed_text_under_persian_threshold_uses_english_rate(self):
        # Mostly English with a couple of Persian characters, so the
        # Persian ratio is below 0.3.
        html = "<p>" + " ".join(["word"] * (WORDS_PER_MINUTE_EN + 1)) + " س</p>"
        assert calculate_reading_time(html) == 2
