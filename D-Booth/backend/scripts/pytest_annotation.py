"""Render concise pytest failures as a GitHub Actions annotation."""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_CASES = 6
MAX_CASE_DETAILS = 2400
MAX_ANNOTATION = 16000
FAILURE_TAGS = {"error", "failure"}
IMPORTANT_LOG_LINE = re.compile(
    r"(FAILED|ERROR|Traceback|AssertionError|ImportError|ModuleNotFoundError|"
    r"short test summary info|_{3,} .* _{3,}|^E\s+)"
)


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


def extract_junit_failures(path: Path) -> str:
    """Return the first failing test cases from a pytest JUnit report."""
    if not path.is_file():
        return ""

    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return ""

    failures: list[str] = []
    for case in root.iter("testcase"):
        result = next((child for child in case if child.tag in FAILURE_TAGS), None)
        if result is None:
            continue

        class_name = case.get("classname", "").strip()
        test_name = case.get("name", "unknown test").strip()
        test_id = "::".join(part for part in (class_name, test_name) if part)
        kind = result.tag.upper()
        message = _clean_text(result.get("message") or result.get("type"))
        details = _clean_text(result.text)[:MAX_CASE_DETAILS]
        parts = [f"{kind}: {test_id}"]
        if message:
            parts.append(message)
        if details and details != message:
            parts.append(details)
        failures.append("\n".join(parts))

        if len(failures) >= MAX_CASES:
            break

    return "\n\n".join(failures)


def extract_log_failures(path: Path) -> str:
    """Extract focused failure lines when pytest did not produce valid JUnit XML."""
    if not path.is_file():
        return "pytest failed without a readable JUnit report or log."

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    selected_indexes: set[int] = set()
    for index, line in enumerate(lines):
        if IMPORTANT_LOG_LINE.search(line):
            selected_indexes.update(range(max(0, index - 2), min(len(lines), index + 7)))

    if not selected_indexes:
        return "\n".join(lines[-80:])
    return "\n".join(lines[index] for index in sorted(selected_indexes))


def build_failure_summary(junit_path: Path, log_path: Path) -> str:
    """Build a bounded annotation body, preferring structured JUnit failures."""
    summary = extract_junit_failures(junit_path) or extract_log_failures(log_path)
    return summary[:MAX_ANNOTATION]


def escape_workflow_command(value: str) -> str:
    """Escape data for a GitHub Actions workflow command."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("junit_path", type=Path)
    parser.add_argument("log_path", type=Path)
    args = parser.parse_args()

    summary = build_failure_summary(args.junit_path, args.log_path)
    print(f"::error title=Backend pytest failed::{escape_workflow_command(summary)}")


if __name__ == "__main__":
    main()
