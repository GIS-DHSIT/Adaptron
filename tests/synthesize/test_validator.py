from adaptron.synthesize.validator import MappingValidator, ValidationReport
from adaptron.ingest.models import RawDocument


def test_validate_all_valid():
    validator = MappingValidator()
    mapping = {"question": "input", "answer": "output"}
    data = [
        RawDocument(content="", metadata={"row": {"question": "What is AI?", "answer": "AI is..."}}),
        RawDocument(content="", metadata={"row": {"question": "What is ML?", "answer": "ML is..."}}),
    ]
    report = validator.validate(mapping, data, "qa")
    assert report.coverage_pct == 100.0
    assert report.approved is True
    assert report.invalid_records == 0


def test_validate_with_null_values():
    validator = MappingValidator()
    mapping = {"question": "input", "answer": "output"}
    data = [
        RawDocument(content="", metadata={"row": {"question": "What?", "answer": "Something"}}),
        RawDocument(content="", metadata={"row": {"question": None, "answer": "Something"}}),
    ]
    report = validator.validate(mapping, data, "qa")
    assert report.invalid_records == 1
    assert report.coverage_pct == 50.0
    assert report.approved is False


def test_validate_nonexistent_column():
    validator = MappingValidator()
    mapping = {"nonexistent": "input"}
    data = [
        RawDocument(content="", metadata={"row": {"question": "What?", "answer": "Something"}}),
    ]
    report = validator.validate(mapping, data, "qa")
    assert report.invalid_records == 1
    assert len(report.errors) > 0


def test_validate_high_coverage_needs_confirmation():
    validator = MappingValidator()
    mapping = {"question": "input", "answer": "output"}
    data = [
        RawDocument(content="", metadata={"row": {"question": f"Q{i}", "answer": f"A{i}"}})
        for i in range(99)
    ] + [
        RawDocument(content="", metadata={"row": {"question": None, "answer": "A100"}}),
    ]
    report = validator.validate(mapping, data, "qa")
    assert 99.0 <= report.coverage_pct < 100.0
    assert report.approved is True  # 99% is auto-approved with notification
