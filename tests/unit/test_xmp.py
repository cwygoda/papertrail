"""Unit tests for XMP sidecar generation and conversion."""

from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

from papertrail.adapters.metadata.xmp import (
    build_xmp,
    convert_yaml_to_xmp,
    write_xmp_sidecar,
)
from papertrail.domain.models import DocumentInfo


class TestBuildXmp:
    """Tests for build_xmp."""

    def test_basic_fields(self) -> None:
        info = DocumentInfo(
            title="Test Invoice",
            subject="Payment Due",
            issuer="Acme Corp",
            summary="Invoice for services",
            date=date(2024, 3, 15),
        )
        xmp = build_xmp(info, "test.pdf")

        # Check XML declaration and xpacket wrapper
        assert xmp.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert '<?xpacket begin="\ufeff"' in xmp
        assert xmp.strip().endswith('<?xpacket end="w"?>')

        # Parse and verify content (strip processing instructions)
        lines = xmp.split("\n")
        xml_content = "\n".join(line for line in lines if not line.startswith("<?"))
        root = ET.fromstring(xml_content)

        # Verify namespaces present
        assert "adobe:ns:meta/" in root.tag

    def test_rdf_alt_structure(self) -> None:
        """Verify XMP spec compliant rdf:Alt with xml:lang."""
        info = DocumentInfo(
            title="Test Title",
            subject="Test Subject",
            issuer="Test Issuer",
            summary="Test Summary",
            date=None,
        )
        xmp = build_xmp(info, "test.pdf")

        # Check rdf:Alt structure with x-default language
        assert "rdf:Alt" in xmp
        assert 'xml:lang="x-default"' in xmp
        assert "Test Title" in xmp
        assert "Test Subject" in xmp

    def test_steuerrelevant_label(self) -> None:
        info = DocumentInfo(
            title="Tax Doc",
            subject="Tax",
            issuer="Tax Office",
            summary="Tax document",
            date=None,
            steuerrelevant=True,
        )
        xmp = build_xmp(info, "tax.pdf")

        assert "Steuerrelevant" in xmp
        assert "<pt:steuerrelevant>true</pt:steuerrelevant>" in xmp

    def test_no_steuerrelevant(self) -> None:
        info = DocumentInfo(
            title="Regular Doc",
            subject="General",
            issuer="Company",
            summary="Regular document",
            date=None,
            steuerrelevant=False,
        )
        xmp = build_xmp(info, "doc.pdf")

        # xmp:Label should not be present
        assert "xmp:Label" not in xmp or "Steuerrelevant" not in xmp
        assert "<pt:steuerrelevant>false</pt:steuerrelevant>" in xmp

    def test_no_date(self) -> None:
        info = DocumentInfo(
            title="Undated",
            subject="Unknown",
            issuer="Unknown",
            summary="No date",
            date=None,
        )
        xmp = build_xmp(info, "undated.pdf")

        # dc:date should not be present when date is None
        assert "dc:date" not in xmp

    def test_xml_special_chars_escaped(self) -> None:
        """Ensure XML special characters are properly escaped."""
        info = DocumentInfo(
            title="Invoice <2024> & Sons",
            subject='Quote "Special"',
            issuer="O'Reilly & Associates",
            summary="Amount: <$100> & tax",
            date=None,
        )
        xmp = build_xmp(info, "special.pdf")

        # ElementTree handles escaping automatically
        assert "&lt;2024&gt;" in xmp
        assert "&amp;" in xmp
        # Verify it's valid XML by parsing
        lines = xmp.split("\n")
        xml_content = "\n".join(line for line in lines if not line.startswith("<?"))
        ET.fromstring(xml_content)  # Should not raise


class TestWriteXmpSidecar:
    """Tests for write_xmp_sidecar."""

    def test_creates_xmp_file(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.touch()

        info = DocumentInfo(
            title="Test",
            subject="Test",
            issuer="Test",
            summary="Test",
            date=date(2024, 1, 1),
        )

        result = write_xmp_sidecar(pdf, info)

        assert result == tmp_path / "doc.xmp"
        assert result.exists()
        content = result.read_text()
        assert '<?xpacket begin="\ufeff"' in content


class TestConvertYamlToXmp:
    """Tests for convert_yaml_to_xmp."""

    def test_basic_conversion(self, tmp_path: Path) -> None:
        yaml_content = """title: Invoice 123
subject: Monthly Bill
issuer: Utility Co
date: "2024-06-15"
summary: Electric bill for June
steuerrelevant: true
processed_at: "2024-06-20T10:30:00"
source_file: scan.pdf
"""
        yaml_path = tmp_path / "doc.yaml"
        yaml_path.write_text(yaml_content)

        xmp_path = convert_yaml_to_xmp(yaml_path)

        assert xmp_path == tmp_path / "doc.xmp"
        assert xmp_path.exists()

        content = xmp_path.read_text()
        assert "Invoice 123" in content
        assert "Monthly Bill" in content
        assert "Utility Co" in content
        assert "2024-06-15" in content
        assert "Steuerrelevant" in content

    def test_missing_optional_fields(self, tmp_path: Path) -> None:
        yaml_content = """title: Minimal Doc
subject: Minimal
issuer: Someone
summary: Brief
"""
        yaml_path = tmp_path / "minimal.yaml"
        yaml_path.write_text(yaml_content)

        xmp_path = convert_yaml_to_xmp(yaml_path)

        assert xmp_path.exists()
        content = xmp_path.read_text()
        assert "Minimal Doc" in content
        assert "<pt:steuerrelevant>false</pt:steuerrelevant>" in content

    def test_preserves_yaml(self, tmp_path: Path) -> None:
        yaml_content = """title: Test
subject: Test
issuer: Test
summary: Test
"""
        yaml_path = tmp_path / "keep.yaml"
        yaml_path.write_text(yaml_content)

        convert_yaml_to_xmp(yaml_path)

        # YAML should still exist
        assert yaml_path.exists()
