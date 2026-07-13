import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.manage_alaveteli_queue import merge_queue


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_merge_queue_removes_only_completed_requests(tmp_path: Path) -> None:
    queue = tmp_path / "queue.jsonl"
    ledger = tmp_path / "ledger.jsonl"
    incoming = tmp_path / "incoming.jsonl"
    output = tmp_path / "out.jsonl"
    write_jsonl(queue, [{"request_id": 1, "url_title": "one"}])
    write_jsonl(ledger, [{"request_id": 1, "status": "completed"}, {"request_id": 2, "status": "failed"}])
    write_jsonl(incoming, [{"request_id": 2, "url_title": "two"}, {"request_id": 3, "url_title": "three"}])

    result = merge_queue(queue=queue, ledger=ledger, incoming=incoming, output=output)

    assert result == {"discovered": 3, "completed": 1, "pending": 2, "queue_empty": False}
    assert [json.loads(line)["request_id"] for line in output.read_text().splitlines()] == [2, 3]


def test_merge_queue_is_empty_after_all_verified_completions(tmp_path: Path) -> None:
    queue = tmp_path / "queue.jsonl"
    ledger = tmp_path / "ledger.jsonl"
    output = tmp_path / "out.jsonl"
    write_jsonl(queue, [{"request_id": "slug", "url_title": "slug"}])
    write_jsonl(ledger, [{"request_id": "slug", "status": "completed"}])

    result = merge_queue(queue=queue, ledger=ledger, incoming=None, output=output)

    assert result["queue_empty"] is True
    assert output.read_text(encoding="utf-8") == ""
