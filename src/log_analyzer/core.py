"""
Core log analysis logic.
"""

import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
_LEVEL_ORDER = {level: index for index, level in enumerate(LOG_LEVELS)}
_LEVEL_ALIASES = {
    "WARN": "WARNING",
    "FATAL": "CRITICAL",
}
_LEVEL_PATTERN = r"DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL"
_CLOCK = r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
_FRACTION = r"(?:[.,]\d+)?"
_TIMEZONE = r"(?:Z|[+-]\d{2}:?\d{2})?"

# Bracket format keeps the historical timestamp (no fractional seconds).
_BRACKET_RE = re.compile(
    rf"^\s*(?P<ts>{_CLOCK}){_FRACTION}.*?\[(?P<level>{_LEVEL_PATTERN})\]\s*(?P<msg>.*)$",
    re.IGNORECASE,
)
_DASH_SIMPLE_RE = re.compile(
    rf"^\s*(?P<ts>{_CLOCK}{_FRACTION}{_TIMEZONE})\s+-\s+"
    rf"(?P<level>{_LEVEL_PATTERN})\s+-\s*(?P<msg>.*)$",
    re.IGNORECASE,
)
_DASH_LOGGER_RE = re.compile(
    rf"^\s*(?P<ts>{_CLOCK}{_FRACTION}{_TIMEZONE})\s+-\s+\S+\s+-\s+"
    rf"(?P<level>{_LEVEL_PATTERN})\s+-\s*(?P<msg>.*)$",
    re.IGNORECASE,
)
_BASIC_RE = re.compile(
    rf"^\s*(?P<level>{_LEVEL_PATTERN}):(?P<logger>[^:\s]+):(?P<msg>.*)$",
    re.IGNORECASE,
)
_EXC_HEADER_RE = re.compile(
    r"^(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*"
    r"(?:Error|Exception|Interrupt|Exit|Warning|Iteration|Group)\b(?::.*)?$"
)
_CONTEXT_PREFIXES = (
    "During handling of the above exception, another exception occurred:",
    "The above exception was the direct cause of the following exception:",
)
_TRACEBACK_MARK = "Traceback (most recent call last)"


def _open_log(file_path: Path):
    """Open a log as text, skipping a leading UTF-8 BOM if one is present."""
    return open(file_path, "r", encoding="utf-8-sig", errors="ignore")


def _canonical_level(level: str) -> str:
    key = level.upper()
    return _LEVEL_ALIASES.get(key, key)


def normalize_level(level: str) -> str:
    """Return the canonical severity name for a user-supplied level.

    ``WARN`` is ``WARNING`` and ``FATAL`` is ``CRITICAL``. Surrounding
    whitespace and case are ignored. Unknown names raise ``ValueError``.
    """
    if level is None:
        raise ValueError("log level is required")
    key = _canonical_level(str(level).strip())
    if key not in _LEVEL_ORDER:
        known = ", ".join(LOG_LEVELS)
        raise ValueError(
            f"unknown log level {level!r}; expected one of {known} (aliases: WARN, FATAL)"
        )
    return key


def parse_log_line(line: str) -> Optional[Dict]:
    """Parse a single log line and extract level, timestamp, and message.

    Recognized shapes:

    * ``2026-09-18 10:00:00 [LEVEL] message`` (fractional seconds optional)
    * ``2026-09-18 10:00:00,123 - LEVEL - message``
    * ``2026-09-18 10:00:00,123 - logger - LEVEL - message``
    * ``LEVEL:logger:message`` (logging's default ``basicConfig`` format)
    """
    for pattern in (_BRACKET_RE, _DASH_SIMPLE_RE, _DASH_LOGGER_RE, _BASIC_RE):
        match = pattern.match(line)
        if not match:
            continue
        groups = match.groupdict()
        return {
            "timestamp": groups.get("ts") or "",
            "level": _canonical_level(groups["level"]),
            "message": groups["msg"].strip(),
            "raw": line,
        }
    return None


def analyze_levels(file_path: Path) -> Dict[str, int]:
    """Count log entries by level."""
    counts = Counter({level: 0 for level in LOG_LEVELS})

    with _open_log(file_path) as handle:
        for line in handle:
            parsed = parse_log_line(line)
            if parsed:
                counts[parsed["level"]] += 1

    return dict(counts)


def search_keyword(file_path: Path, keyword: str, case_sensitive: bool = False) -> List[str]:
    """Search for a literal keyword in a log file.

    An empty keyword is rejected. Every line contains the empty string, so
    treating it as a match would return the whole file.
    """
    if not isinstance(keyword, str) or keyword == "":
        raise ValueError("keyword must not be empty")

    needle = keyword if case_sensitive else keyword.lower()
    results = []

    with _open_log(file_path) as handle:
        for line_num, line in enumerate(handle, 1):
            haystack = line if case_sensitive else line.lower()
            if needle in haystack:
                results.append(f"Line {line_num}: {line.strip()}")

    return results


def filter_by_level(file_path: Path, level: str) -> List[str]:
    """Filter log entries by minimum level.

    ``level`` must be a known severity (or the ``WARN`` / ``FATAL`` aliases).
    Unknown values raise ``ValueError`` instead of silently returning every line.
    """
    min_idx = _LEVEL_ORDER[normalize_level(level)]
    results = []

    with _open_log(file_path) as handle:
        for line_num, line in enumerate(handle, 1):
            parsed = parse_log_line(line)
            if parsed and _LEVEL_ORDER[parsed["level"]] >= min_idx:
                results.append(f"Line {line_num}: {line.strip()}")

    return results


def _payload(line: str) -> str:
    parsed = parse_log_line(line)
    if parsed is not None:
        return parsed["message"]
    return line.strip()


def _is_traceback_start(line: str) -> bool:
    return _TRACEBACK_MARK in line


def _is_file_line(payload: str) -> bool:
    return payload.startswith("File ")


def _is_caret(payload: str) -> bool:
    return bool(payload) and "^" in payload and set(payload) <= set("^~")


def _is_exception_header(payload: str) -> bool:
    return _EXC_HEADER_RE.match(payload) is not None


def _is_context_line(payload: str) -> bool:
    return payload.startswith(_CONTEXT_PREFIXES)


def _is_indented_body(raw: str) -> bool:
    """True for classic indented frames and for log lines whose message is indented.

    A single space after ``[LEVEL]`` or ``- LEVEL -`` is the normal separator.
    Traceback frames carried on a log line use a deeper indent (``[ERROR]   File ...``).
    """
    if raw.startswith((" ", "\t")):
        return True
    bracket = re.search(
        rf"\[(?:{_LEVEL_PATTERN})\]([ \t]*)\S",
        raw,
        re.IGNORECASE,
    )
    if bracket and len(bracket.group(1)) >= 2 and parse_log_line(raw) is not None:
        return True
    dashed = re.search(
        rf" - (?:{_LEVEL_PATTERN}) -([ \t]*)\S",
        raw,
        re.IGNORECASE,
    )
    return bool(dashed and len(dashed.group(1)) >= 2)


def _belongs_to_traceback(raw: str, *, expect_source: bool, seen_header: bool) -> bool:
    if expect_source:
        return True
    payload = _payload(raw)
    if (
        _is_indented_body(raw)
        or _is_caret(payload)
        or _is_file_line(payload)
        or _is_exception_header(payload)
        or _is_context_line(payload)
    ):
        return True
    # A multi-line exception message continues until the next log record.
    return seen_header and parse_log_line(raw) is None


def extract_exceptions(file_path: Path) -> List[str]:
    """Extract Python traceback blocks from a log file.

    A block starts at ``Traceback (most recent call last)`` and keeps its
    frames, caret lines, and exception text, including a message that spans
    lines. The next log record is not swallowed. If another traceback starts
    before the current one has an exception line, the partial block is kept.
    """
    exceptions: List[str] = []
    current: List[str] = []
    in_traceback = False
    expect_source = False
    seen_header = False

    def flush() -> None:
        nonlocal current, in_traceback, expect_source, seen_header
        text = "\n".join(current).rstrip()
        if text:
            exceptions.append(text)
        current = []
        in_traceback = False
        expect_source = False
        seen_header = False

    with _open_log(file_path) as handle:
        for line in handle:
            raw = line.rstrip("\r\n")
            if _is_traceback_start(raw):
                if in_traceback:
                    flush()
                in_traceback = True
                expect_source = False
                seen_header = False
                current = [raw]
                continue
            if not in_traceback:
                continue
            if not _belongs_to_traceback(raw, expect_source=expect_source, seen_header=seen_header):
                flush()
                continue

            current.append(raw)
            payload = _payload(raw)
            if expect_source:
                expect_source = False
            elif _is_file_line(payload):
                expect_source = True
            if _is_exception_header(payload):
                seen_header = True

    if in_traceback:
        flush()

    return exceptions
