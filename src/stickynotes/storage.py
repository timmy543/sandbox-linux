"""Ukladani poznamek do JSON souboru v ~/.local/share/stickynotes-timmy543/."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path


def data_dir() -> Path:
    """Linux: ~/.local/share/stickynotes-timmy543, Windows: %LOCALAPPDATA%\\stickynotes-timmy543."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "stickynotes-timmy543"


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
        self._mtime: int | None = None
        self.load()

    def _stat_mtime(self) -> int | None:
        try:
            return self.path.stat().st_mtime_ns
        except OSError:
            return None

    def reload_if_changed(self) -> bool:
        """Znovu nacte soubor, pokud ho mezitim prepsal nekdo jiny.

        Aplikace i widget bezi jako samostatne procesy nad jednim souborem.
        Bez tohohle by kazdy zapis vysypal na disk celou vlastni (zastaralou)
        kopii seznamu a prepsal tak zmeny toho druheho.
        """
        if self._mtime is not None and self._stat_mtime() == self._mtime:
            return False
        self.load()
        return True

    def load(self) -> None:
        self._mtime = self._stat_mtime()
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
        # Zadne razeni: poradi v souboru = poradi vzniku, prvni vytvorena je
        # prvni. Musi byt stabilni, protoze widget listuje podle indexu a
        # ukazuje "x/y" - drivejsi razeni podle `updated` seznam preskladalo
        # pokazde, co se neco ulozilo, a cislovani skakalo pod rukama.
        self.notes = [Note.from_dict(item) for item in raw.get("notes", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        payload = {"version": 1, "notes": [asdict(n) for n in self.notes]}
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)
        self._mtime = self._stat_mtime()

    def add(self) -> Note:
        self.reload_if_changed()
        note = Note()
        self.notes.append(note)  # na konec = poradi vzniku
        self.save()
        return note

    def get(self, note_id: str) -> Note | None:
        return next((n for n in self.notes if n.id == note_id), None)

    def update(self, note_id: str, *, title: str | None = None, body: str | None = None) -> None:
        # Read-modify-write: nacteme cerstvy stav z disku a zmenime jen tuhle
        # jednu poznamku. Zapis pak nesmaze, co mezitim ulozila druha strana.
        self.reload_if_changed()
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
        self.reload_if_changed()
        self.notes = [n for n in self.notes if n.id != note_id]
        self.save()
