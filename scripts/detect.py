"""
E2 file detection utilities.

Checks whether raw .yxdb bytes are E1, E2, or unknown format.
"""

import struct
import re

E1_MAGIC = b"Alteryx Database File"
E2_MAGIC = b"Alteryx e2 Database file"


def detect_format(data: bytes) -> str:
    """Return 'E1', 'E2', or 'UNKNOWN' for raw .yxdb bytes."""
    if len(data) < 100:
        return "UNKNOWN"
    magic = data[:64]
    if magic.startswith(E2_MAGIC):
        return "E2"
    if magic.startswith(E1_MAGIC):
        return "E1"
    return "UNKNOWN"


def extract_e2_metadata(data: bytes) -> dict | None:
    """Extract basic metadata from E2 file bytes. Returns None if not E2."""
    if detect_format(data) != "E2":
        return None
    meta_size = struct.unpack_from("<I", data, 96)[0]
    xml = data[100 : 100 + meta_size].decode("utf-8", errors="replace")
    field_names = re.findall(r'name="([^"]+)"', xml)
    field_types = sorted(set(re.findall(r'type="([^"]+)"', xml)))
    return {
        "field_count": len(field_names),
        "field_names": field_names,
        "field_types": field_types,
    }
