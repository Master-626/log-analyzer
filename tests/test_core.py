import pytest
from pathlib import Path
from log_analyzer.core import analyze_levels, search_keyword, filter_by_level, extract_exceptions


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
    assert len(exceptions) >= 1
    assert "Traceback" in exceptions[0]
