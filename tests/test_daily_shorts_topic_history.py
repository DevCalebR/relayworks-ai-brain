import json
from pathlib import Path

from tools import shorts_batch


def _topic(name, title=None):
    return {
        "topic": name,
        "suggested_title": title or name,
    }


class FakeResearch:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0) if self.responses else []


def test_normalize_topic_treats_simple_variants_as_duplicates():
    variants = [
        "The Island Nobody Was Allowed to Visit",
        "the island nobody was allowed to visit",
        "The Island Nobody Was Allowed To Visit!",
        "  The   Island Nobody Was Allowed to Visit  ",
    ]

    assert {shorts_batch.normalize_topic(topic) for topic in variants} == {
        "the island nobody was allowed to visit"
    }


def test_existing_topic_history_prevents_reuse(tmp_path, monkeypatch):
    history_path = tmp_path / "memory" / "daily_shorts_topics.json"
    history_path.parent.mkdir(parents=True)
    history_path.write_text(
        json.dumps(
            [
                {
                    "topic": "The Island Nobody Was Allowed to Visit",
                    "normalized_topic": shorts_batch.normalize_topic(
                        "The Island Nobody Was Allowed to Visit"
                    ),
                }
            ]
        ),
        encoding="utf-8",
    )
    fake_research = FakeResearch(
        [
            [
                _topic("The Island Nobody Was Allowed To Visit!"),
                _topic("The Clock That Stopped a Trial"),
            ]
        ]
    )
    monkeypatch.setattr(shorts_batch, "research_topics", fake_research)

    plan = shorts_batch._topic_records(
        "weird history",
        "mystery fans",
        1,
        batch_id="batch-001",
        first_used_at="2026-05-07T10:00:00",
        topic_history_path=history_path,
    )

    assert [record["topic"] for record in plan["records"]] == [
        "The Clock That Stopped a Trial"
    ]
    assert plan["reused_topics_skipped"] == 1


def test_duplicate_topics_in_one_response_are_skipped(tmp_path, monkeypatch):
    fake_research = FakeResearch(
        [
            [
                _topic("The Island Nobody Was Allowed to Visit"),
                _topic("the island nobody was allowed to visit!"),
                _topic("The Cave That Changed a Kingdom"),
            ]
        ]
    )
    monkeypatch.setattr(shorts_batch, "research_topics", fake_research)

    plan = shorts_batch._topic_records(
        "weird history",
        "mystery fans",
        2,
        batch_id="batch-001",
        first_used_at="2026-05-07T10:00:00",
        topic_history_path=tmp_path / "memory" / "daily_shorts_topics.json",
    )

    assert [record["topic"] for record in plan["records"]] == [
        "The Island Nobody Was Allowed to Visit",
        "The Cave That Changed a Kingdom",
    ]
    assert plan["duplicate_topics_skipped"] == 1


def test_retry_attempts_when_first_response_has_too_few_fresh_topics(
    tmp_path,
    monkeypatch,
):
    fake_research = FakeResearch(
        [
            [_topic("The Trial That Made No Sense")],
            [
                _topic("The Bell That Rang by Itself"),
                _topic("The Road That Vanished From Maps"),
            ],
        ]
    )
    monkeypatch.setattr(shorts_batch, "research_topics", fake_research)

    plan = shorts_batch._topic_records(
        "weird history",
        "mystery fans",
        2,
        batch_id="batch-001",
        first_used_at="2026-05-07T10:00:00",
        topic_history_path=tmp_path / "memory" / "daily_shorts_topics.json",
    )

    assert plan["topic_generation_attempts"] == 2
    assert len(plan["records"]) == 2
    assert fake_research.calls[1]["avoid_topics"] == ["The Trial That Made No Sense"]


def test_topic_shortfall_does_not_raise_runtime_error(tmp_path, monkeypatch):
    fake_research = FakeResearch(
        [
            [_topic("The Trial That Made No Sense")],
            [_topic("the trial that made no sense!")],
        ]
    )
    monkeypatch.setattr(shorts_batch, "research_topics", fake_research)

    plan = shorts_batch._topic_records(
        "weird history",
        "mystery fans",
        2,
        batch_id="batch-001",
        first_used_at="2026-05-07T10:00:00",
        topic_history_path=tmp_path / "memory" / "daily_shorts_topics.json",
    )

    assert len(plan["records"]) == 1
    assert plan["topic_shortfall"] is True
    assert "You requested 2 Shorts" in plan["topic_shortfall_warning"]


def test_batch_summary_records_shortfall_and_saves_history(tmp_path, monkeypatch):
    history_path = tmp_path / "memory" / "daily_shorts_topics.json"
    fake_research = FakeResearch(
        [
            [_topic("The Trial That Made No Sense")],
            [_topic("the trial that made no sense!")],
        ]
    )

    def fake_script(*args, **kwargs):
        return "A strange case stayed unsolved. Like and subscribe."

    def fake_pipeline(topic, script, args):
        run_folder = Path(args.run_folder)
        run_folder.mkdir(parents=True, exist_ok=True)
        paths = {
            "video": run_folder / "video.mp4",
            "audio": run_folder / "audio.mp3",
            "captions": run_folder / "captions.srt",
            "script": run_folder / "script.txt",
            "metadata": run_folder / "metadata.json",
        }
        paths["video"].write_bytes(b"fake video")
        paths["audio"].write_bytes(b"fake audio")
        paths["captions"].write_text("1\n00:00:00,000 --> 00:00:01,000\nFake\n")
        paths["script"].write_text(script, encoding="utf-8")
        paths["metadata"].write_text(
            json.dumps({"title": topic, "description": topic}),
            encoding="utf-8",
        )

        return {
            "run_folder": str(run_folder),
            "upload_check_result": {"ready": True},
            **{key: str(path) for key, path in paths.items()},
        }

    monkeypatch.setattr(shorts_batch, "DAILY_BATCHES_OUTPUT_DIR", tmp_path / "batches")
    monkeypatch.setattr(shorts_batch, "TOPIC_HISTORY_PATH", history_path)
    monkeypatch.setattr(shorts_batch, "research_topics", fake_research)
    monkeypatch.setattr(shorts_batch, "generate_short_script", fake_script)
    monkeypatch.setattr(shorts_batch, "run_full_generation_pipeline", fake_pipeline)

    summary = shorts_batch.create_daily_shorts_batch(
        niche="weird history",
        audience="mystery fans",
        count=2,
        generate_thumbnail=False,
        upload_ready_check=False,
    )

    assert summary["count_requested"] == 2
    assert summary["count_planned"] == 1
    assert summary["topic_shortfall"] is True
    assert summary["topic_history_checked"] is True
    assert summary["fresh_topics_generated"] == 1
    assert summary["topic_generation_attempts"] == 2
    assert summary["reused_topics_skipped"] == 0
    assert summary["topic_history_path"] == str(history_path)
    assert "You requested 2 Shorts" in summary["topic_shortfall_warning"]

    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert [record["normalized_topic"] for record in history] == [
        "the trial that made no sense"
    ]
    assert history[0]["batch_id"] == summary["batch_id"]
    assert history[0]["short_number"] == 1

    next_steps = Path(summary["next_steps_path"]).read_text(encoding="utf-8")
    assert "Topic history checked: yes" in next_steps
    assert "Fresh topics generated: 1" in next_steps
    assert "Previously used topics skipped: 0" in next_steps
    assert "You requested 2 Shorts" in next_steps


def test_planner_runs_do_not_reuse_previous_topics(tmp_path, monkeypatch):
    history_path = tmp_path / "memory" / "daily_shorts_topics.json"

    first_research = FakeResearch(
        [
            [
                _topic("The First Fresh Mystery"),
                _topic("The Second Fresh Mystery"),
            ]
        ]
    )
    monkeypatch.setattr(shorts_batch, "research_topics", first_research)

    first_plan = shorts_batch._topic_records(
        "weird history",
        "mystery fans",
        2,
        batch_id="batch-001",
        first_used_at="2026-05-07T10:00:00",
        topic_history_path=history_path,
    )

    assert len(first_plan["records"]) == 2

    second_research = FakeResearch(
        [
            [
                _topic("the first fresh mystery!"),
                _topic("The Third Fresh Mystery"),
                _topic("The Fourth Fresh Mystery"),
            ]
        ]
    )
    monkeypatch.setattr(shorts_batch, "research_topics", second_research)

    second_plan = shorts_batch._topic_records(
        "weird history",
        "mystery fans",
        2,
        batch_id="batch-002",
        first_used_at="2026-05-07T11:00:00",
        topic_history_path=history_path,
    )

    assert [record["topic"] for record in second_plan["records"]] == [
        "The Third Fresh Mystery",
        "The Fourth Fresh Mystery",
    ]
    assert second_plan["reused_topics_skipped"] == 1
