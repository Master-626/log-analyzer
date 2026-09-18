"""
Core log analysis logic.
"""

import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple


LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def parse_log_line(line: str) -> Optional[Dict]:
    """Parse a single log line and extract level, timestamp, message."""
    # Common pattern: 2026-09-18 10:00:00 [LEVEL] message
    pattern = r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}).*?\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]\s*(.*)"
    match = re.match(pattern, line)

    if match:
        return {
            "timestamp": match.group(1),
            "level": match.group(2),
            "message": match.group(3).strip(),
            "raw": line,
        }

    return None


def analyze_levels(file_path: Path) -> Dict[str, int]:
    """Count log entries by level."""
    counts = Counter(level: 0 for level in LOG_LEVELS)

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parsed = parse_log_line(line)
            if parsed:
                counts[parsed["level"]] += 1

    return dict(counts)


def search_keyword(file_path: Path, keyword: str, case_sensitive: bool = False) -> List[str]:
    """Search for keyword in log file."""
    results = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line_num, line in enumerate(f, 1):
            if case_sensitive:
                if keyword in line:
                    results.append(f"Line {line_num}: {line.strip()}")
            else:
                if keyword.lower() in line.lower():
                    results.append(f"Line {line_num}: {line.strip()}")

    return results


def filter_by_level(file_path: Path, level: str) -> List[str]:
    """Filter log entries by minimum level."""
    level_order = {lvl: i for i, lvl in enumerate(LOG_LEVELS)}
    min_level_idx = level_order.get(level.upper(), 0)

    results = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line_num, line in enumerate(f, 1):
            parsed = parse_log_line(line)
            if parsed and level_order.get(parsed["level"], 0) >= min_level_idx:
                results.append(f"Line {line_num}: {line.strip()}")

    return results


def extract_exceptions(file_path: Path) -> List[str]:
    """Extract exception tracebacks from log file."""
    exceptions = []
    current_exception = []
    in_traceback = False

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "Traceback (most recent call last)" in line:
                in_traceback = True
                current_exception = [line.strip()]
            elif in_traceback:
                current_exception.append(line.strip())
                # Traceback ends when we hit a non-indented line or next log entry
                if line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                    exceptions.append("\n".join(current_exception))
                    current_exception = []
                    in_traceback = False

    # Don't forget the last one
    if current_exception:
        exceptions.append("\n".join(current_exception))

    return exceptions
