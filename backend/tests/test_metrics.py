from app.services.coach.metrics import compute_metrics, count_fillers, script_coverage


def test_count_fillers_counts_phrases_once():
    counts = count_fillers("Um, so you know, I think, uh, you know, it's like, kind of good. Umm.")
    assert counts["you know"] == 2
    assert counts["um"] == 1 and counts["umm"] == 1
    assert counts["uh"] == 1
    assert counts["like"] == 1
    assert counts["kind of"] == 1


def test_count_fillers_ignores_substrings():
    assert count_fillers("The umbrella was humming in the summer") == {}


def test_script_coverage_tracks_missed_terms():
    ideal = "Prioritize tasks using the Eisenhower matrix. Block focused time on your calendar."
    coverage, missed = script_coverage("I prioritize my tasks and block time on my calendar", ideal)
    assert 0 < coverage < 1
    assert "eisenhower" in missed
    assert "calendar" not in missed


def test_compute_metrics_ignores_edge_silence():
    m = compute_metrics(
        duration_sec=60.0,
        silences=[(0.0, 1.5), (20.0, 23.0), (40.0, 40.8), (59.0, 60.0)],
        transcript=" ".join(["word"] * 150) + " um uh",
        ideal_text=" ".join(["ideal"] * 140),
        ideal_duration_sec=60.0,
    )
    assert m["pause_count"] == 2  # leading and trailing silence excluded
    assert m["longest_pause_sec"] == 3.0
    assert m["long_pauses"] == [{"at_sec": 20.0, "duration_sec": 3.0}]
    assert m["wpm"] == 152.0
    assert m["ideal_wpm"] == 140.0
    assert m["filler_word_count"] == 2
    assert m["duration_ratio"] == 1.0


def test_compute_metrics_without_transcript():
    m = compute_metrics(
        duration_sec=30.0, silences=[], transcript=None, ideal_text="hello world", ideal_duration_sec=None
    )
    assert m["has_transcript"] is False
    assert "wpm" not in m
    assert m["duration_ratio"] is None
