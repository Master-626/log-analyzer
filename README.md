# Log Analyzer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

A smart CLI tool to analyze log files. Get error statistics, search keywords, filter by level, and extract exceptions quickly.

## 🌟 Features

- 📊 **Level Statistics** - Count log entries by level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- 🔍 **Keyword Search** - Search for specific keywords or patterns in your logs
- 🎚️ **Level Filtering** - Filter entries by minimum severity level
- 🚨 **Exception Extraction** - Automatically extract Python tracebacks and exceptions
- 🎨 **Rich Output** - Beautiful colored terminal output with tables

## 📦 Installation

```bash
git clone https://github.com/Master-626/log-analyzer.git
cd log-analyzer
pip install .
```

## 🚀 Usage

### Show Statistics
```bash
log-analyzer stats app.log
```

### Search Keyword
```bash
log-analyzer search app.log --keyword "database"
```

### Filter by Level
```bash
# Show only ERROR and above
log-analyzer filter app.log --level ERROR
```

### Extract Exceptions
```bash
log-analyzer exceptions app.log
```

## 🧪 Testing

```bash
pip install -e ".[dev]"
pytest
```

## 📄 License

MIT License
