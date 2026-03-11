"""Contract tests for validation module — structured errors and jsonschema."""
from __future__ import annotations

from programmatic_pid.types import SpecValidationError
from programmatic_pid.validation import collect_issues, validate_spec, validate_spec_json


def _minimal_spec():
    return {
        "project": {"id": "P-1", "title": "Test PID", "drawing": {"text_height": 2.0}},
        "equipment": [
            {"id": "E-1", "x": 0, "y": 0, "width": 10, "height": 10},
            {"id": "E-2", "x": 20, "y": 0, "width": 10, "height": 10},
        ],
    }


def test_validate_spec_accepts_valid():
    validate_spec(_minimal_spec())  # should not raise


def test_validate_spec_rejects_missing_project_id():
    spec = _minimal_spec()
    spec["project"]["id"] = ""
    try:
        validate_spec(spec)
        raise AssertionError("Expected SpecValidationError")
    except SpecValidationError:
        pass


def test_collect_issues_returns_structured_errors():
    spec = _minimal_spec()
    spec["equipment"].append({"id": "E-1", "x": 50, "y": 0, "width": 10, "height": 10})
    issues = collect_issues(spec)
    assert any("duplicate" in i.message for i in issues)
    assert all(i.path for i in issues)  # all have paths


def test_validate_spec_json_returns_dicts():
    spec = _minimal_spec()
    spec["equipment"][0]["width"] = 0  # non-positive
    result = validate_spec_json(spec)
    assert isinstance(result, list)
    assert all(isinstance(d, dict) for d in result)
    assert any("non-positive" in d["message"] for d in result)


def test_validate_spec_json_empty_for_valid():
    result = validate_spec_json(_minimal_spec())
    assert result == []


def test_collect_issues_checks_stream_references():
    spec = _minimal_spec()
    spec["streams"] = [
        {"id": "S-1", "from": {"equipment": "NONEXISTENT"}, "to": {"equipment": "E-2"}}
    ]
    issues = collect_issues(spec)
    assert any("NONEXISTENT" in i.message for i in issues)


def test_collect_issues_checks_control_loop_references():
    spec = _minimal_spec()
    spec["instruments"] = [{"id": "PT-1", "tag": "PT-1"}]
    spec["control_loops"] = [
        {"id": "PIC-1", "measurement": "PT-1", "final_element": "MISSING"}
    ]
    issues = collect_issues(spec)
    assert any("MISSING" in i.message for i in issues)


def test_validation_issue_severity_defaults_to_error():
    spec = _minimal_spec()
    spec["equipment"] = []
    issues = collect_issues(spec)
    assert all(i.severity == "error" for i in issues)
