"""Tests for the pure note-log core (no Home Assistant runtime required)."""

from custom_components.device_notes import const, notelog


def test_append_puts_newest_entry_first():
    log = [{"ts": "2026-01-01T00:00:00", "source": "user", "text": "old"}]
    entry = {"ts": "2026-01-02T00:00:00", "source": "agent", "text": "new"}

    result = notelog.append(log, entry)

    assert result[0] == entry
    assert [e["text"] for e in result] == ["new", "old"]


def test_make_entry_sets_all_fields():
    entry = notelog.make_entry("hello", source="agent", ts="2026-01-01T00:00:00")

    assert entry == {
        "ts": "2026-01-01T00:00:00",
        "source": "agent",
        "text": "hello",
        "category": None,
        "severity": const.SEVERITY_INFO,
    }


def test_make_entry_truncates_text_to_max_chars():
    entry = notelog.make_entry("x" * 300, source="agent", ts="t")

    assert len(entry["text"]) == const.MAX_ENTRY_CHARS


def test_make_entry_strips_surrounding_whitespace():
    entry = notelog.make_entry("  hello  ", source="user", ts="t")

    assert entry["text"] == "hello"


def test_prune_keeps_only_newest_max_entries():
    log = [{"ts": str(i), "source": "agent", "text": f"n{i}"} for i in range(60)]

    result = notelog.prune(
        log, max_entries=const.MAX_ENTRIES, max_bytes=const.MAX_LOG_BYTES
    )

    assert len(result) == const.MAX_ENTRIES
    assert result[0] == log[0]  # newest preserved
    assert result[-1] == log[const.MAX_ENTRIES - 1]  # dropped the oldest tail


def test_prune_enforces_byte_budget_dropping_oldest():
    big = "x" * const.MAX_ENTRY_CHARS
    log = [
        {"ts": f"2026-01-01T00:00:{i:02d}", "source": "agent", "text": big}
        for i in range(const.MAX_ENTRIES)
    ]

    result = notelog.prune(
        log, max_entries=const.MAX_ENTRIES, max_bytes=const.MAX_LOG_BYTES
    )

    assert notelog.log_bytes(result) <= const.MAX_LOG_BYTES
    assert result[0] == log[0]  # newest preserved
    assert len(result) < const.MAX_ENTRIES  # oldest pruned to fit the byte budget


def test_append_enforces_caps_so_callers_cannot_forget():
    log = [
        {"ts": str(i), "source": "agent", "text": f"n{i}"}
        for i in range(const.MAX_ENTRIES)
    ]
    entry = notelog.make_entry("newest", source="user", ts="t")

    result = notelog.append(log, entry)

    assert len(result) == const.MAX_ENTRIES
    assert result[0] == entry  # newest kept, oldest dropped


def test_delete_last_removes_the_newest_entry():
    log = [
        {"ts": "t2", "source": "agent", "text": "newest"},
        {"ts": "t1", "source": "user", "text": "older"},
    ]

    result = notelog.delete_last(log)

    assert result == [{"ts": "t1", "source": "user", "text": "older"}]


def test_delete_last_on_empty_log_is_safe():
    assert notelog.delete_last([]) == []


def test_preview_is_empty_for_empty_log():
    assert notelog.preview([]) == ""


def test_preview_shows_latest_text_only():
    log = [{"ts": "2026-01-02T09:30:00", "source": "agent", "text": "fixed boiler"}]

    result = notelog.preview(log)

    assert result == "fixed boiler"  # short, single-line, no timestamp noise


def test_preview_collapses_newlines_and_whitespace():
    log = [{"ts": "t", "source": "agent", "text": "line one\n  line   two\tend"}]

    assert notelog.preview(log) == "line one line two end"


def test_preview_truncates_long_text_with_ellipsis():
    log = [{"ts": "t", "source": "agent", "text": "x" * 255}]

    result = notelog.preview(log)

    assert len(result) <= const.MAX_PREVIEW_CHARS
    assert result.endswith("…")


def test_delete_at_removes_the_entry_with_matching_ts():
    log = [
        {"ts": "t3", "source": "agent", "text": "c"},
        {"ts": "t2", "source": "user", "text": "b"},
        {"ts": "t1", "source": "agent", "text": "a"},
    ]

    assert [e["text"] for e in notelog.delete_at(log, "t2")] == ["c", "a"]


def test_delete_at_unknown_ts_leaves_log_unchanged():
    log = [{"ts": "t1", "source": "agent", "text": "a"}]

    assert notelog.delete_at(log, "nope") == log


def test_make_entry_defaults_severity_info_and_null_category():
    entry = notelog.make_entry("hello", source="agent", ts="t")

    assert entry["severity"] == const.SEVERITY_INFO
    assert entry["category"] is None


def test_make_entry_records_category_and_severity():
    entry = notelog.make_entry(
        "valve stuck", source="agent", ts="t", category="maintenance", severity="error"
    )

    assert entry["category"] == "maintenance"
    assert entry["severity"] == "error"


def test_issue_count_counts_warning_and_error_only():
    log = [
        {"ts": "t4", "source": "agent", "text": "d", "severity": "error"},
        {"ts": "t3", "source": "agent", "text": "c", "severity": "warning"},
        {"ts": "t2", "source": "agent", "text": "b", "severity": "info"},
        {"ts": "t1", "source": "user", "text": "a"},  # legacy entry, no severity
    ]

    assert notelog.issue_count(log) == 2


def test_issue_count_is_zero_for_empty_log():
    assert notelog.issue_count([]) == 0
