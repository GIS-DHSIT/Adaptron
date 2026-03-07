import pytest
from pathlib import Path
from adaptron.ingest.pdf import PDFIngester
from adaptron.ingest.models import DataSource, SourceType


def test_pdf_ingester_supported_types():
    ingester = PDFIngester()
    assert "pdf" in ingester.supported_types()


def test_pdf_ingester_missing_file():
    ingester = PDFIngester()
    source = DataSource(source_type=SourceType.PDF, path="/nonexistent/file.pdf")
    with pytest.raises(FileNotFoundError):
        ingester.ingest(source)


def test_pdf_ingester_extracts_text(tmp_path):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab not installed")
    pdf_path = tmp_path / "test.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 750, "Hello Adaptron")
    c.drawString(100, 730, "This is a test document for ingestion.")
    c.showPage()
    c.save()
    ingester = PDFIngester()
    source = DataSource(source_type=SourceType.PDF, path=str(pdf_path))
    docs = ingester.ingest(source)
    assert len(docs) >= 1
    full_text = " ".join(d.content for d in docs)
    assert "Adaptron" in full_text
