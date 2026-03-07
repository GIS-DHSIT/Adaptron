from adaptron.connectors.cleaner import DataCleaner, CleanConfig
from adaptron.ingest.models import RawDocument


def test_remove_empty_documents():
    cleaner = DataCleaner()
    docs = [
        RawDocument(content="Hello world", source_ref="a.txt"),
        RawDocument(content="", source_ref="b.txt"),
        RawDocument(content="   ", source_ref="c.txt"),
    ]
    result = cleaner.clean(docs, CleanConfig(remove_empty=True))
    assert len(result.cleaned) == 1
    assert result.removed_count == 2


def test_dedup_exact():
    cleaner = DataCleaner()
    docs = [
        RawDocument(content="Same content here", source_ref="a.txt"),
        RawDocument(content="Same content here", source_ref="b.txt"),
        RawDocument(content="Different content", source_ref="c.txt"),
    ]
    result = cleaner.clean(docs, CleanConfig(dedup=True))
    assert len(result.cleaned) == 2
    assert result.dedup_count == 1


def test_normalize_whitespace():
    cleaner = DataCleaner()
    docs = [RawDocument(content="Hello   world\n\n\nfoo   bar", source_ref="a.txt")]
    result = cleaner.clean(docs, CleanConfig(normalize_whitespace=True, remove_empty=False, dedup=False))
    assert "  " not in result.cleaned[0].content


def test_min_content_length():
    cleaner = DataCleaner()
    docs = [
        RawDocument(content="Short", source_ref="a.txt"),
        RawDocument(content="This is a sufficiently long document", source_ref="b.txt"),
    ]
    result = cleaner.clean(docs, CleanConfig(min_content_length=10, dedup=False))
    assert len(result.cleaned) == 1


def test_fix_encoding():
    cleaner = DataCleaner()
    docs = [RawDocument(content="café naïve", source_ref="a.txt")]
    result = cleaner.clean(docs, CleanConfig(fix_encoding=True, dedup=False, remove_empty=False))
    assert len(result.cleaned) == 1


def test_strip_html():
    cleaner = DataCleaner()
    docs = [RawDocument(content="<p>Hello <b>world</b></p>", source_ref="a.txt")]
    result = cleaner.clean(docs, CleanConfig(strip_html=True, dedup=False, remove_empty=False))
    assert "<p>" not in result.cleaned[0].content
    assert "Hello" in result.cleaned[0].content


def test_clean_report():
    cleaner = DataCleaner()
    docs = [
        RawDocument(content="Good content", source_ref="a.txt"),
        RawDocument(content="", source_ref="b.txt"),
    ]
    result = cleaner.clean(docs, CleanConfig())
    assert "removed_empty" in result.report
