# Log Analyzer

## 中文摘要

log-analyzer 是一个分析日志文件的命令行工具。它可以统计各级别条数、按关键字搜索、按最低严重级别过滤，并提取 Python 异常堆栈。

支持 `时间 [LEVEL] 消息`，以及 Python logging 常见格式：`时间 - 级别 - 消息`、`时间 - logger - 级别 - 消息`，还有默认的 `LEVEL:logger:message`。`WARN` 按 `WARNING` 处理，`FATAL` 按 `CRITICAL` 处理。

开发安装：`pip install -e ".[dev]"`。检查与测试：`ruff check .` 和 `pytest`。

A command-line tool that counts log severity, searches for keywords, filters by minimum level, and pulls Python tracebacks out of a log file.

## Features

- Count entries by level: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Search for a literal keyword, with an optional case-sensitive match
- Keep only entries at or above a severity
- Extract Python traceback blocks, including frames that were written as separate log lines
- Read bracketed logs and common Python `logging` formats in the same file

## Requirements

Python 3.8 or newer. `pip` installs `click` and `rich` releases that match the interpreter: `click` 8.2 and newer need Python 3.10, and `rich` 15 needs Python 3.9.

## Installation

```bash
git clone https://github.com/Master-626/log-analyzer.git
cd log-analyzer
pip install .
```

This installs the `log-analyzer` command. For development, including tests and lint:

```bash
pip install -e ".[dev]"
```

## Supported lines

Blank lines and unrecognized lines are ignored by stats and level filtering. Keyword search still scans every line.

| Format | Example |
| --- | --- |
| Bracket level | `2026-09-18 10:00:00 [ERROR] database down` |
| `logging` asctime | `2026-09-18 10:00:00,123 - ERROR - database down` |
| asctime with logger name | `2026-09-18 10:00:00,123 - app.db - ERROR - database down` |
| `basicConfig` default | `ERROR:app.db:database down` |

The timestamp may use `T` instead of a space (`2026-09-18T10:00:00`) and may include fractional seconds or a timezone offset. Bracket levels are matched without regard to case. `WARN` is counted as WARNING and `FATAL` as CRITICAL.

Severity order, from lowest to highest:

`DEBUG` < `INFO` < `WARNING` < `ERROR` < `CRITICAL`

## Usage

```bash
cat > app.log << 'EOF'
2026-09-18 10:00:00 [INFO] Server started on port 8000
2026-09-18 10:00:01,123 - app.db - ERROR - database down
ERROR:app.db:connection refused
Traceback (most recent call last):
  File "app.py", line 42, in connect
    raise ConnectionError("refused")
ConnectionError: refused
EOF

log-analyzer stats app.log
log-analyzer search app.log --keyword database
log-analyzer filter app.log --level error
log-analyzer exceptions app.log
```

### `stats FILE`

Print a table of how many parsed lines fall on each level, plus the total.

```bash
log-analyzer stats app.log
```

### `search FILE`

Search for a literal keyword. An empty keyword is rejected, because it would match every line.

| Option | Short | Description |
| --- | --- | --- |
| `--keyword TEXT` | `-k` | Required. Matched as plain text, not as a regular expression. |
| `--case-sensitive` | `-c` | Match case exactly. The default search is case-insensitive. |

```bash
log-analyzer search app.log -k "connection refused"
log-analyzer search app.log -k ERROR -c
```

The command prints the first 20 matching lines and a count of any further matches.

### `filter FILE`

Print parsed lines at or above a minimum level. The default is `ERROR`, so ERROR and CRITICAL are shown.

| Option | Short | Description |
| --- | --- | --- |
| `--level LEVEL` | `-l` | One of DEBUG, INFO, WARNING, ERROR, CRITICAL. `WARN` and `FATAL` are accepted. Surrounding spaces are ignored. |

```bash
log-analyzer filter app.log
log-analyzer filter app.log --level warning
log-analyzer filter app.log -l FATAL
```

An unknown level is an error. It does not fall back to showing every line. The first 20 matches are printed.

### `exceptions FILE`

Print Python traceback blocks. A block starts at `Traceback (most recent call last):` and includes the frames and the exception line. The next log record is not included. Up to five tracebacks are printed.

```bash
log-analyzer exceptions app.log
```

### Other options

| Option | Description |
| --- | --- |
| `--help` | Show commands and options. |
| `--version` | Show the installed version. |

`FILE` must be an existing file. A directory path is rejected.

## Running tests and lint

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

GitHub Actions runs the same `ruff check .` and `pytest` commands on Python 3.8, 3.9, 3.10, 3.11, 3.12, and 3.13.

## Library

The CLI calls `log_analyzer.core`. The same functions are safe to import:

| Function | Behavior |
| --- | --- |
| `parse_log_line(line)` | Parse one line, or return `None` when the line is not a recognized record. |
| `analyze_levels(path)` | Return counts for every level, including zeroes. |
| `search_keyword(path, keyword, case_sensitive=False)` | Return `Line N: ...` strings. An empty keyword raises `ValueError`. |
| `filter_by_level(path, level)` | Return lines at or above `level`. An unknown level raises `ValueError`. |
| `normalize_level(level)` | Canonical name, with `WARN` and `FATAL` mapped. |
| `extract_exceptions(path)` | Return each traceback as one string. |

## License

MIT License
