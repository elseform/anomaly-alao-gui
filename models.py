"""
Shared data for the Lua analyzer.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path


def detect_file_encoding(file_path: Path) -> str:
    """Detect file encoding: UTF-8 BOM -> UTF-8 -> CP1251 -> latin-1 fallback.

    CP1251 is checked before latin-1 because many older STALKER mods carry
    Russian comments encoded in Windows-1251. latin-1 will accept any byte
    sequence so it must remain last.
    """
    raw = file_path.read_bytes()
    # UTF-8 BOM
    if raw[:3] == b'\xef\xbb\xbf':
        return 'utf-8-sig'
    # try UTF-8
    try:
        raw.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        pass
    # try CP1251 - common in older Anomaly/CoP scripts.
    # Heuristic: only accept CP1251 if it actually decodes AND contains
    # Cyrillic characters. Without the heuristic almost any byte pattern
    # decodes (CP1251 covers all 256 byte values like latin-1), which would
    # mask other encodings.
    try:
        decoded = raw.decode('cp1251')
        if any('Ѐ' <= ch <= 'ӿ' for ch in decoded):
            return 'cp1251'
    except UnicodeDecodeError:
        pass
    # fallback to latin-1 (maps bytes 0-255 directly, always succeeds)
    return 'latin-1'


@dataclass
class Finding:
    """Represents a single issue found during analysis."""
    pattern_name: str
    severity: str  # GREEN, YELLOW, RED, DEBUG
    line_num: int
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    source_line: str = ""

    # aliases for compatibility
    @property
    def description(self) -> str:
        return self.message

    @property
    def line_content(self) -> str:
        return self.source_line
