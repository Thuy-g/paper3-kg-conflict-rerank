"""Optional cross-encoder reranker (sentence-transformers is imported lazily).

Not installed or tested in the cloud container. Check the model size before downloading
(project rule: no model weights > 100 MB in the cloud).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kgrerank.rerankers.base import Ranking, sort_by_score
from kgrerank.schema import Example


class OptionalDependencyError(ImportError):
    """Raised when an optional heavy dependency is missing."""


@dataclass
class CrossEncoderReranker:
    model_name: str
    max_length: int = 512
    batch_size: int = 16
    name: str = "cross_encoder"
    _model: Any = field(default=None, init=False, repr=False)

    def _load(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as err:  # pragma: no cover - depends on the environment
                raise OptionalDependencyError(
                    "CrossEncoderReranker needs the optional extra: uv pip install -e '.[ce]'"
                ) from err
            self._model = CrossEncoder(self.model_name, max_length=self.max_length)
        return self._model

    def rank(self, example: Example) -> Ranking:
        model = self._load()
        pairs = [(example.question, f"{c.title} {c.text}") for c in example.candidates]
        raw = model.predict(pairs, batch_size=self.batch_size)
        scores = {c.pid: float(s) for c, s in zip(example.candidates, raw, strict=True)}
        return Ranking(
            order=sort_by_score(scores, [c.pid for c in example.candidates]), scores=scores
        )
