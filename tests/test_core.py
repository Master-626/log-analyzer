from pathlib import Path

import pytest

from log_analyzer.core import (
    LOG_LEVELS,
    analyze_levels,
    extract_exceptions,
    filter_by_level,
    normalize_level,
    parse_log_line,
    search_keyword,
)


@pytest.fixture
def sample_log_file(tmp_path: Path):
    """Create a sample log file for testing."""
    log_content = """2026-09-18 10:00:00 [INFO] Server started on port 8000
2026-09-18 10:00:01 [DEBUG] Loading configuration
2026-09-18 10:00:02 [WARNING] High memory usage detected
2026-09-18 10:00:03 [ERROR] Database connection failed
Traceback (most recent call last):
  File "app.py", line 42, in connect
    raise ConnectionError()
ConnectionError: Connection refused
2026-09-18 10:00:04 [ERROR] Retry failed
2026-09-18 10:00:05 [CRITICAL] System out of memory
"""
    log_file = tmp_path / "test.log"
    log_file.write_text(log_content)
    return log_file


def test_analyze_levels(sample_log_file):
    """Test log level statistics."""
    counts = analyze_levels(sample_log_file)
    assert counts["INFO"] == 1
    assert counts["DEBUG"] == 1
    assert counts["WARNING"] == 1
    assert counts["ERROR"] == 2
    assert counts["CRITICAL"] == 1


def test_search_keyword(sample_log_file):
    """Test keyword search."""
    results = search_keyword(sample_log_file, "error")
    assert len(results) >= 2


def test_filter_by_level(sample_log_file):
    """Test level filtering."""
    results = filter_by_level(sample_log_file, "ERROR")
    assert len(results) == 3  # 2 ERROR + 1 CRITICAL


def test_extract_exceptions(sample_log_file):
    """Test exception extraction."""
    exceptions = extract_exceptions(sample_log_file)
    assert len(exceptions) == 1
    assert "Traceback (most recent call last):" in exceptions[0]
    assert 'File "app.py", line 42, in connect' in exceptions[0]
    assert "ConnectionError: Connection refused" in exceptions[0]
    assert "Retry failed" not in exceptions[0]
    # Frame indentation is part of the traceback, not something to strip away.
    assert "\n  File \"app.py\"" in exceptions[0]


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content)
    return path


def test_parse_bracket_line_keeps_timestamp_without_fraction():
    """Fractional seconds stay outside the timestamp, as they always have."""
    parsed = parse_log_line("2026-09-18 10:00:00.123 [INFO] ok\n")
    assert parsed == {
        "timestamp": "2026-09-18 10:00:00",
        "level": "INFO",
        "message": "ok",
        "raw": "2026-09-18 10:00:00.123 [INFO] ok\n",
    }


def test_bracket_level_in_the_message_does_not_override_the_real_level():
    parsed = parse_log_line("2026-09-18 10:00:00 [INFO] see [ERROR] code")
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "see [ERROR] code"


def test_parse_lowercase_level_and_leading_whitespace():
    parsed = parse_log_line("  2026-09-18T10:00:00 [error] boom")
    assert parsed["timestamp"] == "2026-09-18T10:00:00"
    assert parsed["level"] == "ERROR"
    assert parsed["message"] == "boom"


def test_warn_and_fatal_aliases_are_counted(tmp_path):
    path = _write(
        tmp_path,
        "alias.log",
        "2026-09-18 10:00:00 [WARN] disk\n2026-09-18 10:00:01 [FATAL] dead\n",
    )
    counts = analyze_levels(path)
    assert counts["WARNING"] == 1
    assert counts["CRITICAL"] == 1
    assert counts["ERROR"] == 0


def test_utf8_bom_does_not_hide_first_line(tmp_path):
    path = tmp_path / "bom.log"
    path.write_bytes("\ufeff2026-09-18 10:00:00 [ERROR] boom\n".encode("utf-8"))
    assert analyze_levels(path)["ERROR"] == 1
    assert parse_log_line(path.read_text(encoding="utf-8-sig"))["level"] == "ERROR"


def test_python_logging_formats_are_counted(tmp_path):
    """stdlib asctime and basicConfig lines count toward the same levels."""
    path = _write(
        tmp_path,
        "app.log",
        "\n".join(
            [
                "2026-09-18 10:00:00 [INFO] bracket still counts",
                "2026-09-18 10:00:00,123 - ERROR - database down",
                "2026-09-18 10:00:01,123 - app.db - WARNING - slow query",
                "2026-09-18T10:00:02+00:00 - CRITICAL - disk full",
                "INFO:root:ready",
                "ERROR:app.db:connection refused",
                "WARN:root:retrying",
            ]
        )
        + "\n",
    )
    assert analyze_levels(path) == {
        "DEBUG": 0,
        "INFO": 2,
        "WARNING": 2,
        "ERROR": 2,
        "CRITICAL": 1,
    }
    dashed = parse_log_line("2026-09-18 10:00:00,123 - ERROR - database down")
    assert dashed["timestamp"] == "2026-09-18 10:00:00,123"
    assert dashed["level"] == "ERROR"
    assert dashed["message"] == "database down"
    with_logger = parse_log_line("2026-09-18 10:00:01,123 - app.db - WARNING - slow query")
    assert with_logger["level"] == "WARNING"
    assert with_logger["message"] == "slow query"
    basic = parse_log_line("ERROR:app.db:connection refused")
    assert basic["timestamp"] == ""
    assert basic["level"] == "ERROR"
    assert basic["message"] == "connection refused"


def test_filter_includes_python_logging_lines(tmp_path):
    path = _write(
        tmp_path,
        "app.log",
        "2026-09-18 10:00:00,123 - INFO - ok\n"
        "2026-09-18 10:00:01,123 - my.logger - ERROR - down\n"
        "CRITICAL:app:dead\n",
    )
    results = filter_by_level(path, "error")
    assert [line.split(": ", 1)[1] for line in results] == [
        "2026-09-18 10:00:01,123 - my.logger - ERROR - down",
        "CRITICAL:app:dead",
    ]


def test_empty_file(tmp_path):
    path = _write(tmp_path, "empty.log", "")
    assert analyze_levels(path) == {level: 0 for level in LOG_LEVELS}
    assert search_keyword(path, "anything") == []
    assert filter_by_level(path, "DEBUG") == []
    assert extract_exceptions(path) == []


def test_search_keyword_is_literal_and_reports_line_numbers(sample_log_file):
    results = search_keyword(sample_log_file, "Server started")
    assert results == ["Line 1: 2026-09-18 10:00:00 [INFO] Server started on port 8000"]
    assert search_keyword(sample_log_file, "error", case_sensitive=True) == []
    assert len(search_keyword(sample_log_file, "ERROR", case_sensitive=True)) == 2
    assert search_keyword(sample_log_file, "not-in-the-file") == []


def test_search_keyword_rejects_empty_string(sample_log_file):
    with pytest.raises(ValueError, match="empty"):
        search_keyword(sample_log_file, "")
    with pytest.raises(ValueError, match="empty"):
        search_keyword(sample_log_file, None)


def test_normalize_level_aliases_and_rejects_unknown():
    assert normalize_level(" error ") == "ERROR"
    assert normalize_level("warn") == "WARNING"
    assert normalize_level("FATAL") == "CRITICAL"
    with pytest.raises(ValueError, match="unknown log level"):
        normalize_level("NOPE")
    with pytest.raises(ValueError, match="unknown log level"):
        normalize_level("   ")


def test_filter_by_level_rejects_unknown_instead_of_returning_everything(sample_log_file):
    with pytest.raises(ValueError, match="unknown log level"):
        filter_by_level(sample_log_file, "NOPE")


def test_filter_aliases_do_not_include_lower_severities(sample_log_file):
    fatal = filter_by_level(sample_log_file, "FATAL")
    assert len(fatal) == 1
    assert "CRITICAL" in fatal[0]

    warning_and_above = filter_by_level(sample_log_file, " WARN ")
    assert len(warning_and_above) == 4
    assert all("[INFO]" not in line and "[DEBUG]" not in line for line in warning_and_above)

    assert len(filter_by_level(sample_log_file, " ERROR ")) == 3


def test_extract_prefixed_traceback_keeps_the_exception(tmp_path):
    path = _write(
        tmp_path,
        "prefixed.log",
        "\n".join(
            [
                "2026-09-18 10:00:03 [ERROR] Traceback (most recent call last):",
                '2026-09-18 10:00:03 [ERROR]   File "app.py", line 42, in connect',
                '2026-09-18 10:00:03 [ERROR]     raise ConnectionError("refused")',
                "2026-09-18 10:00:03 [ERROR] ConnectionError: refused",
                "2026-09-18 10:00:04 [INFO] recovered",
            ]
        )
        + "\n",
    )
    found = extract_exceptions(path)
    assert len(found) == 1
    assert 'File "app.py", line 42, in connect' in found[0]
    assert "ConnectionError: refused" in found[0]
    assert "recovered" not in found[0]


def test_extract_dashed_traceback_stops_before_the_next_record(tmp_path):
    path = _write(
        tmp_path,
        "dashed.log",
        "\n".join(
            [
                "2026-09-18 10:00:03,123 - ERROR - Traceback (most recent call last):",
                '2026-09-18 10:00:03,123 - ERROR -   File "app.py", line 42, in connect',
                '2026-09-18 10:00:03,123 - ERROR -     raise ConnectionError("refused")',
                "2026-09-18 10:00:03,123 - ERROR - ConnectionError: refused",
                "2026-09-18 10:00:04,123 - INFO - recovered",
            ]
        )
        + "\n",
    )
    found = extract_exceptions(path)
    assert len(found) == 1
    assert "ConnectionError: refused" in found[0]
    assert "recovered" not in found[0]


def test_extract_does_not_swallow_the_next_log_line(tmp_path):
    path = _write(
        tmp_path,
        "indented.log",
        "\n".join(
            [
                "2026-09-18 10:00:03 [ERROR] failed",
                "    Traceback (most recent call last):",
                '      File "app.py", line 42, in connect',
                "        raise ConnectionError()",
                "    ConnectionError: Connection refused",
                "2026-09-18 10:00:04 [ERROR] Retry failed",
            ]
        )
        + "\n",
    )
    found = extract_exceptions(path)
    assert len(found) == 1
    assert "ConnectionError: Connection refused" in found[0]
    assert "Retry failed" not in found[0]


def test_extract_keeps_multiline_exception_message(tmp_path):
    path = _write(
        tmp_path,
        "multi.log",
        "\n".join(
            [
                "Traceback (most recent call last):",
                '  File "app.py", line 2, in <module>',
                '    raise ValueError("hello\\nworld")',
                "ValueError: hello",
                "world",
                "2026-09-18 10:00:04 [INFO] next",
            ]
        )
        + "\n",
    )
    found = extract_exceptions(path)
    assert len(found) == 1
    assert "ValueError: hello\nworld" in found[0]
    assert "next" not in found[0]


def test_extract_does_not_drop_a_traceback_when_the_next_one_starts(tmp_path):
    path = _write(
        tmp_path,
        "reset.log",
        "\n".join(
            [
                "Traceback (most recent call last):",
                '  File "app.py", line 10, in <module>',
                '    raise ValueError("first")',
                "Traceback (most recent call last):",
                '  File "app.py", line 12, in <module>',
                '    raise RuntimeError("second")',
                "RuntimeError: second",
            ]
        )
        + "\n",
    )
    found = extract_exceptions(path)
    assert len(found) == 2
    assert 'raise ValueError("first")' in found[0]
    assert "RuntimeError: second" in found[1]
    assert 'raise ValueError("first")' not in found[1]


def test_extract_keeps_column_zero_caret_and_syntax_error(tmp_path):
    path = _write(
        tmp_path,
        "syntax.log",
        "\n".join(
            [
                "Traceback (most recent call last):",
                '  File "app.py", line 1',
                "    (",
                "^",
                "SyntaxError: '(' was never closed",
            ]
        )
        + "\n",
    )
    found = extract_exceptions(path)
    assert len(found) == 1
    assert "\n^\nSyntaxError: '(' was never closed" in found[0]


def test_extract_two_complete_tracebacks_stay_separate(tmp_path):
    path = _write(
        tmp_path,
        "two.log",
        "\n".join(
            [
                "Traceback (most recent call last):",
                '  File "app.py", line 5, in <module>',
                "    raise ValueError('first')",
                "ValueError: first",
                "2026-09-18 10:00:04 [ERROR] still going",
                "Traceback (most recent call last):",
                '  File "app.py", line 8, in <module>',
                "    raise RuntimeError('second')",
                "RuntimeError: second",
            ]
        )
        + "\n",
    )
    found = extract_exceptions(path)
    assert len(found) == 2
    assert "ValueError: first" in found[0]
    assert "still going" not in found[0]
    assert "RuntimeError: second" in found[1]
