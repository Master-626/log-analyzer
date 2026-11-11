from click.testing import CliRunner

from log_analyzer.cli import main


def _write(tmp_path, text: str):
    path = tmp_path / "app.log"
    path.write_text(text)
    return path


def test_stats_counts_bracket_and_logging_lines(tmp_path):
    log = _write(
        tmp_path,
        "2026-09-18 10:00:00 [INFO] ready\n"
        "2026-09-18 10:00:01,123 - ERROR - database down\n"
        "CRITICAL:app:disk full\n",
    )
    result = CliRunner().invoke(main, ["stats", str(log)])
    assert result.exit_code == 0
    assert "Total entries: 3" in result.output
    assert "INFO" in result.output
    assert "ERROR" in result.output
    assert "CRITICAL" in result.output


def test_search_prints_brackets_as_text(tmp_path):
    log = _write(tmp_path, "2026-09-18 10:00:00 [INFO] hello [red]hot[/]\n")
    result = CliRunner().invoke(main, ["search", str(log), "-k", "hello"])
    assert result.exit_code == 0
    assert "[red]hot[/]" in result.output
    assert "Found 1 matches" in result.output


def test_search_rejects_empty_keyword(tmp_path):
    log = _write(tmp_path, "2026-09-18 10:00:00 [INFO] hello\n")
    result = CliRunner().invoke(main, ["search", str(log), "-k", ""])
    assert result.exit_code != 0
    assert "empty" in result.output.lower()
    assert "hello" not in result.output


def test_filter_unknown_level_does_not_dump_the_file(tmp_path):
    log = _write(
        tmp_path,
        "2026-09-18 10:00:00 [INFO] hello\n2026-09-18 10:00:01 [ERROR] boom\n",
    )
    result = CliRunner().invoke(main, ["filter", str(log), "-l", "NOPE"])
    assert result.exit_code != 0
    assert "unknown log level" in result.output
    assert "hello" not in result.output
    assert "boom" not in result.output


def test_filter_shows_only_requested_severity(tmp_path):
    log = _write(
        tmp_path,
        "2026-09-18 10:00:00 [INFO] hello\n2026-09-18 10:00:01 [ERROR] boom\n",
    )
    result = CliRunner().invoke(main, ["filter", str(log), "--level", "error"])
    assert result.exit_code == 0
    assert "boom" in result.output
    assert "hello" not in result.output
    assert "ERROR+" in result.output


def test_exceptions_command_prints_traceback(tmp_path):
    log = _write(
        tmp_path,
        "\n".join(
            [
                "2026-09-18 10:00:03 [ERROR] failed",
                "Traceback (most recent call last):",
                '  File "app.py", line 42, in connect',
                "    raise ConnectionError()",
                "ConnectionError: Connection refused",
            ]
        )
        + "\n",
    )
    result = CliRunner().invoke(main, ["exceptions", str(log)])
    assert result.exit_code == 0
    assert "Found 1 exceptions" in result.output
    assert "ConnectionError: Connection refused" in result.output
    assert 'File "app.py", line 42, in connect' in result.output


def test_directory_is_rejected(tmp_path):
    result = CliRunner().invoke(main, ["stats", str(tmp_path)])
    assert result.exit_code != 0
    assert "directory" in result.output.lower()


def test_version_option():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.1" in result.output


def test_help_lists_commands():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    for name in ("stats", "search", "filter", "exceptions"):
        assert name in result.output
