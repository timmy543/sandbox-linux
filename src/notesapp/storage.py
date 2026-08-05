"""Ukladani poznamek do JSON souboru v ~/.local/share/notes-sandbox/."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path


def data_dir() -> Path:
    """Linux: ~/.local/share/notes-sandbox, Windows: %LOCALAPPDATA%\\notes-sandbox."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "notes-sandbox"


@dataclass
class Note:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Nova poznamka"
    body: str = ""
    updated: float = field(default_factory=time.time)

    @classmethod
    def from_dict(cls, raw: dict) -> "Note":
        return cls(
            id=raw.get("id") or uuid.uuid4().hex,
            title=raw.get("title", "Nova poznamka"),
            body=raw.get("body", ""),
            updated=float(raw.get("updated", 0.0)),
        )


class NoteStore:
    """Drzi vsechny poznamky v pameti a atomicky je uklada na disk."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (data_dir() / "notes.json")
        self.notes: list[Note] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.notes = []
            return
        try:
            # utf-8-sig: nekteré editory (a PowerShell) zapisuji UTF-8 s BOM,
            # ktery by cisty utf-8 dekoder povazoval za poskozeny soubor.
            raw = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            # Poskozeny soubor radeji odlozime nez zahodime.
            self.path.replace(self.path.with_suffix(".json.broken"))
            self.notes = []
            return
        self.notes = [Note.from_dict(item) for item in raw.get("notes", [])]
        self._sort()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        payload = {"version": 1, "notes": [asdict(n) for n in self.notes]}
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def _sort(self) -> None:
        self.notes.sort(key=lambda n: n.updated, reverse=True)

    def add(self) -> Note:
        note = Note()
        self.notes.insert(0, note)
        self.save()
        return note

    def get(self, note_id: str) -> Note | None:
        return next((n for n in self.notes if n.id == note_id), None)

    def update(self, note_id: str, *, title: str | None = None, body: str | None = None) -> None:
        note = self.get(note_id)
        if note is None:
            return
        if title is not None:
            note.title = title
        if body is not None:
            note.body = body
        note.updated = time.time()
        self.save()

    def delete(self, note_id: str) -> None:
        self.notes = [n for n in self.notes if n.id != note_id]
        self.save()
