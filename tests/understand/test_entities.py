from adaptron.understand.entities import RegexEntityExtractor


def test_extracts_emails():
    extractor = RegexEntityExtractor()
    entities = extractor.extract("Contact alice@example.com for details.")
    labels = [e.label for e in entities]
    assert "EMAIL" in labels


def test_extracts_dates():
    extractor = RegexEntityExtractor()
    entities = extractor.extract("Meeting on 2026-03-07 at noon.")
    labels = [e.label for e in entities]
    assert "DATE" in labels


def test_extracts_numbers():
    extractor = RegexEntityExtractor()
    entities = extractor.extract("Revenue was $1,234,567.89 in Q4.")
    labels = [e.label for e in entities]
    assert "MONEY" in labels
