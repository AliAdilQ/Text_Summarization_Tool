from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.seed import SAMPLE_ARTICLES
from app.services.summarizer import (
    SummarizerService,
    clean_model_output,
    extractive_summary,
    word_count,
)


def test_extractive_lengths_are_distinct():
    text = SAMPLE_ARTICLES[0][1]
    counts = [
        word_count(extractive_summary(text, length)) for length in ("short", "medium", "long")
    ]
    assert 0 < counts[0] < counts[1] < counts[2] < word_count(text)
    assert all(sentence in text for sentence in extractive_summary(text, "long").split(". ")[:-1])


def test_model_output_drops_incomplete_tail_and_normalizes_punctuation():
    assert (
        clean_model_output("Clean energy is growing . New policies help local")
        == "Clean energy is growing."
    )
    assert (
        clean_model_output("An unusually long opening sentence")
        == "An unusually long opening sentence…"
    )


def test_single_unpunctuated_passage_is_reduced():
    text = " ".join(["energy storage powers communities and improves reliable infrastructure"] * 20)
    assert 0 < word_count(extractive_summary(text)) < word_count(text)


@pytest.mark.parametrize(
    "text,length",
    [("short", "medium"), ("word " * 10001, "short"), (SAMPLE_ARTICLES[0][1], "invalid")],
    ids=["too-short", "too-large", "invalid-length"],
)
def test_service_validation(text, length):
    with pytest.raises(ValueError):
        SummarizerService(backend="extractive").summarize(text, length)


def test_model_load_failure_is_cached(monkeypatch):
    loader = Mock(side_effect=OSError("No cached model"))
    monkeypatch.setitem(
        __import__("sys").modules,
        "transformers",
        SimpleNamespace(
            AutoTokenizer=SimpleNamespace(from_pretrained=loader),
            AutoModelForSeq2SeqLM=SimpleNamespace(from_pretrained=loader),
            pipeline=Mock(),
        ),
    )
    service = SummarizerService()
    assert service.summarize(SAMPLE_ARTICLES[0][1]).method == "extractive"
    assert service.summarize(SAMPLE_ARTICLES[1][1]).method == "extractive"
    assert loader.call_count == 1
    assert loader.call_args.kwargs["local_files_only"] is True


def test_inference_failure_falls_back():
    service = SummarizerService()
    service._pipeline = Mock(side_effect=RuntimeError("Out of memory"))
    service._pipeline.tokenizer = FakeTokenizer()
    service._pipeline.model.config.max_position_embeddings = 1024
    result = service.summarize(SAMPLE_ARTICLES[0][1])
    assert result.method == "extractive"
    assert "unavailable" in result.notice


class FakeTokenizer:
    model_max_length = 50

    def encode(self, text, add_special_tokens=False):
        return text.split()

    def decode(self, tokens, skip_special_tokens=True):
        return " ".join(tokens)


def test_chunking_preserves_all_input_and_token_budget():
    service = SummarizerService(backend="extractive")
    text = SAMPLE_ARTICLES[0][1] + " " + " ".join(f"token{i}" for i in range(100))
    chunks = service.chunk_text(text, FakeTokenizer(), 42)
    assert all(len(chunk.split()) <= 42 for chunk in chunks)
    assert " ".join(chunks) == text


def test_transformer_combines_chunks_and_reduces_again():
    calls = []

    class FakePipeline:
        tokenizer = FakeTokenizer()
        model = SimpleNamespace(config=SimpleNamespace(max_position_embeddings=50))

        def __call__(self, text, **kwargs):
            calls.append((text, kwargs))
            return [
                {
                    "summary_text": "Clear summaries preserve the most important ideas while giving readers enough context to understand the original document and its purpose."
                }
            ]

    service = SummarizerService()
    service._pipeline = FakePipeline()
    result = service.summarize(SAMPLE_ARTICLES[0][1])
    assert result.method == "transformer"
    assert len(calls) > 2
    assert all(len(text.split()) <= 42 for text, _ in calls)
    assert all(kwargs["truncation"] is False for _, kwargs in calls)
    # Reduction preserves the original output budget instead of applying the
    # compression fraction repeatedly until nearly all context is lost.
    assert calls[-1][1]["max_length"] >= 20
    assert result.summary_word_count == 20
