"""XMP sidecar file generation and YAML conversion."""

from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from ...domain.models import DocumentInfo

# XMP namespaces
NS = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xmp": "http://ns.adobe.com/xap/1.0/",
    "pt": "https://papertrail.wygoda.net/ns/1.0/",
    "xml": "http://www.w3.org/XML/1998/namespace",
}

# Register namespaces for clean output
for prefix, uri in NS.items():
    if prefix != "xml":  # xml namespace is implicit
        ET.register_namespace(prefix, uri)


def _tag(ns: str, name: str) -> str:
    """Create namespaced tag."""
    return f"{{{NS[ns]}}}{name}"


def _add_lang_alt(parent: ET.Element, dc_name: str, value: str) -> None:
    """Add Dublin Core element as rdf:Alt with xml:lang (XMP spec compliant)."""
    elem = ET.SubElement(parent, _tag("dc", dc_name))
    alt = ET.SubElement(elem, _tag("rdf", "Alt"))
    li = ET.SubElement(alt, _tag("rdf", "li"))
    li.set(_tag("xml", "lang"), "x-default")
    li.text = value


def build_xmp(info: DocumentInfo, source_file: str) -> str:
    """Build XMP XML string from DocumentInfo."""
    # Root xmpmeta
    xmpmeta = ET.Element(_tag("x", "xmpmeta"))

    # RDF container
    rdf = ET.SubElement(xmpmeta, _tag("rdf", "RDF"))

    # Description with all namespaces
    desc = ET.SubElement(rdf, _tag("rdf", "Description"))
    desc.set(_tag("rdf", "about"), "")

    # Dublin Core with rdf:Alt (XMP spec compliant)
    _add_lang_alt(desc, "title", info.title)
    _add_lang_alt(desc, "subject", info.subject)
    _add_lang_alt(desc, "description", info.summary)

    # dc:creator as rdf:Seq
    creator_elem = ET.SubElement(desc, _tag("dc", "creator"))
    seq = ET.SubElement(creator_elem, _tag("rdf", "Seq"))
    ET.SubElement(seq, _tag("rdf", "li")).text = info.issuer

    # dc:date
    if info.date:
        ET.SubElement(desc, _tag("dc", "date")).text = info.date.isoformat()

    # XMP Label for steuerrelevant
    if info.steuerrelevant:
        ET.SubElement(desc, _tag("xmp", "Label")).text = "Steuerrelevant"

    # Papertrail custom fields
    ET.SubElement(desc, _tag("pt", "steuerrelevant")).text = str(
        info.steuerrelevant
    ).lower()
    ET.SubElement(desc, _tag("pt", "processedAt")).text = datetime.now().isoformat()
    ET.SubElement(desc, _tag("pt", "sourceFile")).text = source_file

    # Serialize with XML declaration and xpacket wrapper
    xml_str = ET.tostring(xmpmeta, encoding="unicode")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        f"{xml_str}\n"
        '<?xpacket end="w"?>\n'
    )


def write_xmp_sidecar(path: Path, info: DocumentInfo) -> Path:
    """Write XMP sidecar file alongside PDF."""
    sidecar_path = path.with_suffix(".xmp")
    xmp_content = build_xmp(info, path.name)
    sidecar_path.write_text(xmp_content, encoding="utf-8")
    return sidecar_path


def convert_yaml_to_xmp(yaml_path: Path) -> Path:
    """Convert YAML sidecar to XMP format.

    Returns path to new XMP file. Does not delete original YAML.
    """
    from datetime import date

    import yaml

    data = yaml.safe_load(yaml_path.read_text())

    # Parse date from ISO string
    doc_date = None
    if data.get("date"):
        doc_date = date.fromisoformat(data["date"])

    info = DocumentInfo(
        title=data.get("title", ""),
        subject=data.get("subject", ""),
        issuer=data.get("issuer", ""),
        summary=data.get("summary", ""),
        date=doc_date,
        steuerrelevant=data.get("steuerrelevant", False),
    )

    source_file = data.get("source_file", yaml_path.stem + ".pdf")
    xmp_path = yaml_path.with_suffix(".xmp")
    xmp_content = build_xmp(info, source_file)
    xmp_path.write_text(xmp_content, encoding="utf-8")
    return xmp_path
