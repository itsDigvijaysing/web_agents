"""JSONL-backed trajectory storage with numpy cosine-similarity search.

Adapted from Agent-S's KnowledgeBase.retrieve_narrative_experience (gui_agents/s2/core/knowledge.py):
same embed -> cosine-similarity -> argsort-descending -> top-k approach, with two deliberate
deviations: numpy only (no scikit-learn, avoids a heavy dependency for a 3-line calculation),
and one append-only JSONL file with embeddings stored inline (no separate JSON + embeddings.pkl
pair that can drift out of sync, and no pickle deserialization risk).
"""

import logging
from pathlib import Path

import portalocker

from web_agent.memory.views import TrajectoryRecord

logger = logging.getLogger(__name__)


class TrajectoryStore:
	def __init__(self, path: str | Path):
		self.path = Path(path)
		self.path.parent.mkdir(parents=True, exist_ok=True)

	def append(self, record: TrajectoryRecord) -> None:
		line = record.model_dump_json() + '\n'
		with open(self.path, 'a') as f:
			portalocker.lock(f, portalocker.LOCK_EX)
			f.write(line)

	def load_all(self) -> list[TrajectoryRecord]:
		if not self.path.exists():
			return []

		records: list[TrajectoryRecord] = []
		with open(self.path) as f:
			portalocker.lock(f, portalocker.LOCK_SH)
			for line_num, line in enumerate(f, start=1):
				line = line.strip()
				if not line:
					continue
				try:
					records.append(TrajectoryRecord.model_validate_json(line))
				except Exception as e:
					logger.warning(f'Skipping corrupt trajectory record at {self.path}:{line_num}: {e}')
		return records

	def search(
		self, query_embedding: list[float], embedding_model: str, top_k: int = 3, min_score: float = 0.75
	) -> list[tuple[TrajectoryRecord, float]]:
		"""Cosine similarity search restricted to records whose embedding_model matches the query's."""
		candidates = [
			r for r in self.load_all() if r.embedding is not None and r.embedding_model == embedding_model
		]
		if not candidates:
			return []

		import numpy as np

		query_vec = np.array(query_embedding)
		candidate_matrix = np.array([r.embedding for r in candidates])

		query_norm = np.linalg.norm(query_vec)
		candidate_norms = np.linalg.norm(candidate_matrix, axis=1)
		with np.errstate(invalid='ignore', divide='ignore'):
			similarities = (candidate_matrix @ query_vec) / (candidate_norms * query_norm)
		similarities = np.nan_to_num(similarities, nan=0.0)

		sorted_indices = np.argsort(similarities)[::-1]

		results: list[tuple[TrajectoryRecord, float]] = []
		for idx in sorted_indices:
			score = float(similarities[idx])
			if score < min_score:
				break
			results.append((candidates[idx], score))
			if len(results) >= top_k:
				break
		return results
