"""Vstupni bod aplikace."""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import APP_ID, __version__
from .window import NotesWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Poznámky")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APP_ID)  # spojí okno se .desktop souborem (ikona v panelu)
    app.setWindowIcon(QIcon.fromTheme(APP_ID, QIcon.fromTheme("accessories-text-editor")))

    window = NotesWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
