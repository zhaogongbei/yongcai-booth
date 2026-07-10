from pathlib import Path

from scripts.pytest_annotation import (
    build_failure_summary,
    escape_workflow_command,
    extract_junit_failures,
)


def test_extract_junit_failures_prefers_structured_failure(tmp_path: Path) -> None:
    junit_path = tmp_path / "pytest-results.xml"
    junit_path.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="1">
    <testcase classname="tests.test_auth" name="test_refresh_rejects_revoked_token">
      <failure message="assert 200 == 401" type="AssertionError">traceback details</failure>
    </testcase>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )

    summary = extract_junit_failures(junit_path)

    assert "FAILURE: tests.test_auth::test_refresh_rejects_revoked_token" in summary
    assert "assert 200 == 401" in summary
    assert "traceback details" in summary


def test_build_failure_summary_falls_back_to_focused_log(tmp_path: Path) -> None:
    log_path = tmp_path / "pytest-output.log"
    log_path.write_text(
        "session start\n"
        "________________ test_example ________________\n"
        "E   AssertionError: expected rejection\n"
        "FAILED tests/test_example.py::test_example\n"
        "coverage row that should not dominate the summary\n",
        encoding="utf-8",
    )

    summary = build_failure_summary(tmp_path / "missing.xml", log_path)

    assert "AssertionError: expected rejection" in summary
    assert "FAILED tests/test_example.py::test_example" in summary


def test_escape_workflow_command_encodes_control_characters() -> None:
    assert escape_workflow_command("50%\r\nfailed") == "50%25%0D%0Afailed"
