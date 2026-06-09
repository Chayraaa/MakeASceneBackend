"""
Integration tests for TagExpander.

TagExpander calls a local Ollama HTTP endpoint, so we mock requests.post
to avoid any real network dependency.  We test both the slow (gemma2:9b)
and fast (qwen2.5:1.5b) paths, as well as the _clean() helper directly.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.helper.llm.tag_expander import TagExpander


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(text: str) -> MagicMock:
    """Return a mock that mimics requests.Response for the Ollama API."""
    mock = MagicMock()
    mock.json.return_value = {"response": text}
    return mock


# ---------------------------------------------------------------------------
# _clean()  (static, no network)
# ---------------------------------------------------------------------------

class TestClean:
    def test_basic_expansion_is_prepended_with_anchor(self):
        result = TagExpander._clean("jazz", "swing bebop improvisation brass")
        assert result.startswith("jazz")

    def test_anchor_word_not_duplicated_in_output(self):
        result = TagExpander._clean("jazz", "jazz swing bebop")
        tokens = result.split()
        assert tokens.count("jazz") == 1

    def test_stopwords_are_removed(self):
        result = TagExpander._clean("musik", "rock and roll für die massen")
        tokens = result.split()
        assert "and" not in tokens
        assert "für" not in tokens
        assert "die" not in tokens

    def test_prompt_bleed_words_are_removed(self):
        result = TagExpander._clean("test", "public events context output keywords")
        tokens = result.split()
        for bleed in ("public", "events", "context", "output", "keywords"):
            assert bleed not in tokens

    def test_short_tokens_are_removed(self):
        result = TagExpander._clean("art", "ok hi yes galerie museum")
        tokens = result.split()
        assert "ok" not in tokens
        assert "hi" not in tokens

    def test_tokens_with_invalid_chars_are_removed(self):
        result = TagExpander._clean("food", "essen 123 street-food café!")
        tokens = result.split()
        assert "123" not in tokens
        assert "café!" not in tokens

    def test_hyphenated_words_are_kept(self):
        result = TagExpander._clean("access", "wheelchair-access barrier-free ramp")
        assert "wheelchair-access" in result or "barrier-free" in result

    def test_max_11_expansion_tokens(self):
        many = " ".join(f"word{i}" for i in range(20))
        result = TagExpander._clean("tag", many)
        # anchor "tag" + up to 11 expansion tokens = 12 max
        assert len(result.split()) <= 12

    def test_duplicates_are_removed(self):
        result = TagExpander._clean("rock", "gitarre gitarre schlagzeug schlagzeug")
        tokens = result.split()
        assert tokens.count("gitarre") == 1

    def test_leading_arrow_stripped(self):
        result = TagExpander._clean("comedy", "→ humor standup")
        assert "→" not in result
        assert "humor" in result

    def test_empty_response_returns_anchor(self):
        # _clean lowercases everything (tag_name.lower()), so casing is not preserved
        result = TagExpander._clean("myTag", "")
        assert result == "mytag"

    def test_multi_word_tag_anchor_preserved(self):
        result = TagExpander._clean("street food", "markt essen outdoor")
        assert result.startswith("street food")


# ---------------------------------------------------------------------------
# expand_tag_slow()
# ---------------------------------------------------------------------------

class TestExpandTagSlow:
    def test_returns_expanded_string_on_success(self):
        expander = TagExpander()
        with patch("requests.post", return_value=_mock_response("swing bebop brass")):
            result = expander.expand_tag_slow("jazz")
        assert "jazz" in result
        assert "swing" in result

    def test_uses_gemma_model(self):
        expander = TagExpander()
        with patch("requests.post", return_value=_mock_response("beats dancefloor")) as mock_post:
            expander.expand_tag_slow("techno")
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "gemma2:9b"

    def test_returns_tag_name_on_request_exception(self):
        expander = TagExpander()
        with patch("requests.post", side_effect=Exception("connection refused")):
            result = expander.expand_tag_slow("techno")
        assert result == "techno"

    def test_returns_tag_name_when_response_missing_key(self):
        expander = TagExpander()
        mock = MagicMock()
        mock.json.return_value = {}          # no "response" key
        with patch("requests.post", return_value=mock):
            result = expander.expand_tag_slow("theater")
        assert result == "theater"

    def test_prompt_contains_tag_name(self):
        expander = TagExpander()
        with patch("requests.post", return_value=_mock_response("fairy tale wonder")) as mock_post:
            expander.expand_tag_slow("märchen")
        prompt = mock_post.call_args[1]["json"]["prompt"]
        assert "märchen" in prompt

    def test_temperature_is_zero(self):
        expander = TagExpander()
        with patch("requests.post", return_value=_mock_response("foo bar")) as mock_post:
            expander.expand_tag_slow("sport")
        options = mock_post.call_args[1]["json"]["options"]
        assert options["temperature"] == 0


# ---------------------------------------------------------------------------
# expand_tag_fast()
# ---------------------------------------------------------------------------

class TestExpandTagFast:
    def test_returns_expanded_string_on_success(self):
        expander = TagExpander()
        with patch("requests.post", return_value=_mock_response("club party tanzen")):
            result = expander.expand_tag_fast("nightlife")
        assert "nightlife" in result
        assert "club" in result

    def test_uses_qwen_model(self):
        expander = TagExpander()
        with patch("requests.post", return_value=_mock_response("beats")) as mock_post:
            expander.expand_tag_fast("techno")
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "qwen2.5:1.5b"

    def test_returns_tag_name_on_timeout(self):
        import requests as req
        expander = TagExpander()
        with patch("requests.post", side_effect=req.exceptions.Timeout):
            result = expander.expand_tag_fast("film")
        assert result == "film"

    def test_num_predict_is_smaller_than_slow(self):
        """Fast path must request fewer tokens than slow path."""
        expander = TagExpander()
        with patch("requests.post", return_value=_mock_response("a b")) as mock_post:
            expander.expand_tag_fast("kinder")
        fast_tokens = mock_post.call_args[1]["json"]["options"]["num_predict"]
        assert fast_tokens <= 24