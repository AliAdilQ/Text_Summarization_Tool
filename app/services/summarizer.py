"""Lazy, token-aware abstractive summarization with an offline sentence ranker."""

import logging
import math
import re
import threading
import time
from collections import Counter
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)
WORD_PATTERN = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)
STOP_WORDS = set(
    "a an and are as at be been but by can could did do does for from had has have he her his how i if in into is it its may more most not of on or our s she should so some such than that the their them there these they this those through to too under up was we were what when where which while who will with would you your".split()
)
LENGTHS = {
    "short": {"ratio": 0.15, "max_tokens": 80, "min_tokens": 15},
    "medium": {"ratio": 0.28, "max_tokens": 150, "min_tokens": 30},
    "long": {"ratio": 0.42, "max_tokens": 240, "min_tokens": 45},
}


def word_count(text):
    return len(WORD_PATTERN.findall(text))


def split_sentences(text):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if part.strip()]


def clean_model_output(text):
    """Normalize decoded punctuation and avoid a trailing unfinished sentence."""
    text = re.sub(r"\s+([.,!?;:])", r"\1", text.strip())
    sentences = split_sentences(text)
    if len(sentences) > 1 and not re.search(r"[.!?][\"')\]]?$", sentences[-1]):
        return " ".join(sentences[:-1])
    return text if re.search(r"[.!?][\"')\]]?$", text) else text.rstrip(",;:") + "…"


def extractive_summary(text, length="medium"):
    """Rank meaningful sentences and restore source order within a word budget."""
    sentences = split_sentences(text)
    if len(sentences) < 2:
        words = text.split()
        sentences = [" ".join(words[i : i + 30]) for i in range(0, len(words), 30)]
    total = word_count(text)
    budget = max(
        12,
        min(
            int(total * LENGTHS[length]["ratio"]),
            {"short": 100, "medium": 200, "long": 320}[length],
        ),
    )
    frequencies = Counter(
        word.lower() for word in WORD_PATTERN.findall(text) if word.lower() not in STOP_WORDS
    )
    ranked = []
    for index, sentence in enumerate(sentences):
        tokens = WORD_PATTERN.findall(sentence.lower())
        score = sum(
            frequencies[token] for token in set(tokens) if token not in STOP_WORDS
        ) / math.sqrt(max(len(tokens), 1))
        ranked.append((score * (1.12 if index == 0 else 1), index, sentence))
    selected, used = [], 0
    for _, index, sentence in sorted(ranked, reverse=True):
        count = word_count(sentence)
        if used + count <= budget:
            selected.append((index, sentence))
            used += count
    if not selected:
        sentence = max(ranked)[2]
        return " ".join(sentence.split()[:budget]).rstrip(",;:") + "…"
    return " ".join(sentence for _, sentence in sorted(selected))


@dataclass
class SummaryResult:
    summary: str
    length: str
    original_word_count: int
    summary_word_count: int
    compression_ratio: float
    processing_time: float
    method: str
    notice: str

    def to_dict(self):
        return asdict(self)


class SummarizerService:
    def __init__(
        self, model_name="sshleifer/distilbart-cnn-12-6", backend="auto", allow_download=False
    ):
        if backend not in {"auto", "transformer", "extractive"}:
            raise ValueError("SUMMARIZER_BACKEND must be auto, transformer, or extractive.")
        self.model_name = model_name
        self.backend = backend
        self.allow_download = allow_download
        self._pipeline = None
        self._load_failed = False
        self._lock = threading.RLock()

    def load_model(self):
        """Only try once per worker after a failed load; never download implicitly."""
        with self._lock:
            if self._pipeline is not None:
                return self._pipeline
            if self.backend == "extractive" or self._load_failed:
                return None
            try:
                from transformers import AutoTokenizer

                tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name, local_files_only=not self.allow_download
                )
                from transformers import AutoModelForSeq2SeqLM, pipeline

                model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.model_name, local_files_only=not self.allow_download
                )
                self._pipeline = pipeline(
                    "summarization", model=model, tokenizer=tokenizer, device=-1
                )
            except Exception:
                self._load_failed = True
                logger.warning(
                    "Transformer unavailable; using extractive summarization.", exc_info=True
                )
            return self._pipeline

    def chunk_text(self, text, tokenizer, token_limit):
        """Prefer sentence boundaries; split oversized sentences by token IDs."""
        chunks, current = [], []
        for sentence in split_sentences(text):
            tokens = tokenizer.encode(sentence, add_special_tokens=False)
            if len(tokens) > token_limit:
                if current:
                    chunks.append(" ".join(current))
                    current = []
                chunks.extend(
                    tokenizer.decode(tokens[i : i + token_limit], skip_special_tokens=True)
                    for i in range(0, len(tokens), token_limit)
                )
                continue
            # Re-tokenize joined sentences to account for tokenization at boundaries.
            candidate = " ".join(current + [sentence])
            if current and len(tokenizer.encode(candidate, add_special_tokens=False)) > token_limit:
                chunks.append(" ".join(current))
                current = []
            current.append(sentence)
        if current:
            chunks.append(" ".join(current))
        return chunks

    def _abstractive(self, text, length, pipe):
        tokenizer = pipe.tokenizer
        model_limit = getattr(pipe.model.config, "max_position_embeddings", 1024)
        token_limit = min(tokenizer.model_max_length, model_limit, 1024) - 8
        settings = LENGTHS[length]
        combined = text
        target_tokens = None
        for _ in range(4):
            chunks = self.chunk_text(combined, tokenizer, token_limit)
            if target_tokens is None:
                source_tokens = sum(
                    len(tokenizer.encode(chunk, add_special_tokens=False)) for chunk in chunks
                )
                target_tokens = max(
                    8, min(settings["max_tokens"], int(source_tokens * settings["ratio"]))
                )
            outputs = []
            for chunk in chunks:
                input_size = len(tokenizer.encode(chunk, add_special_tokens=False))
                maximum = max(8, min(target_tokens, int(input_size * 0.7)))
                minimum = min(settings["min_tokens"], max(3, maximum // 2))
                generated = pipe(
                    chunk,
                    max_length=maximum,
                    min_length=minimum,
                    do_sample=False,
                    num_beams=4,
                    truncation=False,
                )[0]["summary_text"].strip()
                if not generated:
                    raise ValueError("The model returned an empty summary.")
                outputs.append(clean_model_output(generated))
            result = " ".join(outputs)
            if len(chunks) == 1:
                return result, "transformer"
            if result == combined:
                break
            combined = result
        # Bound work even for a model that does not reduce its input.
        return extractive_summary(combined, length), "hybrid"

    def summarize(self, text, length="medium"):
        text = text.strip()
        if length not in LENGTHS:
            raise ValueError("Choose Short, Medium, or Long.")
        if len(text) > 50_000:
            raise ValueError("Keep your text under 50,000 characters.")
        original_count = word_count(text)
        if original_count < 30:
            raise ValueError("Add at least 30 words to summarize.")
        started = time.perf_counter()
        notice, method = "", "extractive"
        with self._lock:
            pipe = self.load_model()
            if pipe is not None:
                try:
                    summary, method = self._abstractive(text, length, pipe)
                except Exception:
                    logger.warning(
                        "Model inference failed; using extractive summarization.", exc_info=True
                    )
                    summary = extractive_summary(text, length)
                    notice = "The language model is unavailable. Your summary uses our offline sentence-ranking engine."
            else:
                summary = extractive_summary(text, length)
                notice = "Generated with the offline sentence-ranking engine."
        result_count = word_count(summary)
        compression = round((1 - result_count / original_count) * 100, 1)
        return SummaryResult(
            summary,
            length,
            original_count,
            result_count,
            compression,
            round(max(time.perf_counter() - started, 0.001), 3),
            method,
            notice,
        )
