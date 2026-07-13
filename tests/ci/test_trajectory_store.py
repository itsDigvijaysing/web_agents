"""Tests for the trajectory memory storage layer (schema + JSONL append/load/search).

No network, no LLM, no embedding calls - pure data-layer logic. Mirrors the cosine-similarity
+ argsort approach in Agent-S's gui_agents/s2/core/knowledge.py (adapted: numpy only, no
sklearn; JSONL with inline embeddings, not JSON dict + separate embeddings.pkl).
"""

from web_agent.memory.store import TrajectoryStore
from web_agent.memory.views import TrajectoryRecord


def make_record(task: str, embedding: list[float] | None = None, embedding_model: str | None = None) -> TrajectoryRecord:
	return TrajectoryRecord(
		created_at='2026-07-13T00:00:00',
		task=task,
		success=True,
		final_result='done',
		summary=f'Summary for: {task}',
		key_steps=['step 1', 'step 2'],
		urls_visited=['https://example.com'],
		errors=[],
		number_of_steps=2,
		duration_seconds=1.5,
		embedding=embedding,
		embedding_model=embedding_model,
	)


def test_trajectory_record_has_generated_id():
	record = make_record('Find the weather')
	assert record.id
	other = make_record('Find the weather')
	assert record.id != other.id, 'each record should get a unique id'


def test_store_append_and_load_all_round_trip(tmp_path):
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	record = make_record('Buy groceries online')

	store.append(record)
	loaded = store.load_all()

	assert len(loaded) == 1
	assert loaded[0].task == 'Buy groceries online'
	assert loaded[0].id == record.id


def test_store_append_multiple_and_load_preserves_order(tmp_path):
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	store.append(make_record('Task A'))
	store.append(make_record('Task B'))
	store.append(make_record('Task C'))

	loaded = store.load_all()

	assert [r.task for r in loaded] == ['Task A', 'Task B', 'Task C']


def test_store_load_all_on_missing_file_returns_empty(tmp_path):
	store = TrajectoryStore(path=tmp_path / 'does_not_exist.jsonl')
	assert store.load_all() == []


def test_store_load_all_skips_blank_and_corrupt_lines(tmp_path):
	path = tmp_path / 'trajectories.jsonl'
	good = make_record('Valid task')
	path.write_text(f'\n{good.model_dump_json()}\nnot valid json\n\n')

	store = TrajectoryStore(path=path)
	loaded = store.load_all()

	assert len(loaded) == 1
	assert loaded[0].task == 'Valid task'


def test_search_ranks_by_cosine_similarity(tmp_path):
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	# orthogonal-ish vectors so ranking is unambiguous
	store.append(make_record('close match', embedding=[1.0, 0.0, 0.0], embedding_model='fake-model'))
	store.append(make_record('far match', embedding=[0.0, 1.0, 0.0], embedding_model='fake-model'))
	store.append(make_record('exact match', embedding=[1.0, 0.0, 0.0], embedding_model='fake-model'))

	results = store.search(query_embedding=[1.0, 0.0, 0.0], embedding_model='fake-model', top_k=2, min_score=0.0)

	assert len(results) == 2
	tasks_by_score = [r[0].task for r in results]
	assert tasks_by_score[0] in ('close match', 'exact match')
	assert results[0][1] >= results[1][1], 'results must be sorted descending by score'


def test_search_filters_by_embedding_model(tmp_path):
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	store.append(make_record('model A record', embedding=[1.0, 0.0], embedding_model='model-a'))
	store.append(make_record('model B record', embedding=[1.0, 0.0], embedding_model='model-b'))

	results = store.search(query_embedding=[1.0, 0.0], embedding_model='model-a', top_k=5, min_score=0.0)

	assert len(results) == 1
	assert results[0][0].task == 'model A record'


def test_search_respects_min_score_floor(tmp_path):
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	store.append(make_record('orthogonal', embedding=[0.0, 1.0], embedding_model='fake-model'))

	results = store.search(query_embedding=[1.0, 0.0], embedding_model='fake-model', top_k=5, min_score=0.5)

	assert results == []


def test_search_ignores_records_without_embeddings(tmp_path):
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	store.append(make_record('no embedding', embedding=None, embedding_model=None))
	store.append(make_record('has embedding', embedding=[1.0, 0.0], embedding_model='fake-model'))

	results = store.search(query_embedding=[1.0, 0.0], embedding_model='fake-model', top_k=5, min_score=0.0)

	assert len(results) == 1
	assert results[0][0].task == 'has embedding'


def test_search_on_empty_store_returns_empty(tmp_path):
	store = TrajectoryStore(path=tmp_path / 'trajectories.jsonl')
	assert store.search(query_embedding=[1.0, 0.0], embedding_model='fake-model', top_k=3, min_score=0.0) == []
