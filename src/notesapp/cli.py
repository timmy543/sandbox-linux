"""Pomocne CLI pro Plasma widget.

QML neumi zapisovat soubory, takze plasmoid vola tenhle prikaz pres
Plasma5Support executable datasource. Data chodi jako base64, aby se
nemusely resit uvozovky v shellu.

Pouziti:
    notes-sandbox-store load                -> vypise JSON se vsemi poznamkami
    notes-sandbox-store save <base64-json>  -> ulozi jednu poznamku {id,title,body}
    notes-sandbox-store new                 -> vytvori poznamku, vypise ji
    notes-sandbox-store delete <id>         -> smaze poznamku
"""

from __future__ import annotations

import base64
import binascii
import json
import sys
from dataclasses import asdict

from .storage import NoteStore


def _dump(payload: dict) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def _all_notes(store: NoteStore) -> dict:
    return {"notes": [asdict(n) for n in store.notes]}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv[0] if argv else "load"
    store = NoteStore()

    if command == "load":
        _dump(_all_notes(store))
        return 0

    if command == "new":
        note = store.add()
        _dump({"note": asdict(note), **_all_notes(store)})
        return 0

    if command == "save":
        if len(argv) < 2:
            print("chybi base64 argument", file=sys.stderr)
            return 2
        try:
            raw = json.loads(base64.b64decode(argv[1], validate=True).decode("utf-8"))
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"nevalidni payload: {exc}", file=sys.stderr)
            return 2
        note_id = raw.get("id")
        if not note_id or store.get(note_id) is None:
            print("neznama poznamka", file=sys.stderr)
            return 3
        store.update(note_id, title=raw.get("title"), body=raw.get("body"))
        _dump(_all_notes(store))
        return 0

    if command == "delete":
        if len(argv) < 2:
            print("chybi id", file=sys.stderr)
            return 2
        store.delete(argv[1])
        _dump(_all_notes(store))
        return 0

    print(f"neznamy prikaz: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
