"""Hlavni okno aplikace (Qt6 / PySide6)."""

from __future__ import annotations

import time

from PySide6.QtCore import QFileSystemWatcher, Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .storage import Note, NoteStore

AUTOSAVE_DELAY_MS = 600
NOTE_ID_ROLE = Qt.ItemDataRole.UserRole


class NotesWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Poznámky")
        self.resize(960, 640)

        self.store = NoteStore()
        self._current: Note | None = None
        self._loading = False

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(AUTOSAVE_DELAY_MS)
        self._save_timer.timeout.connect(self._save_now)

        self._build_actions()
        self._build_ui()
        self.setStatusBar(QStatusBar())

        self.refresh_list()
        self._setup_watcher()

    # -------------------------------------------------- Sdileni s widgetem --

    def _setup_watcher(self) -> None:
        """Hlida notes.json, aby se zmeny z Plasma widgetu projevily hned."""
        self._watcher = QFileSystemWatcher(self)
        # Hlida se i adresar: soubor se uklada atomicky pres rename, cimz se
        # zmeni inode a watcher by o puvodni cestu prisel.
        self.store.path.parent.mkdir(parents=True, exist_ok=True)
        self._watcher.addPath(str(self.store.path.parent))
        if self.store.path.exists():
            self._watcher.addPath(str(self.store.path))

        # Debounce: rename generuje nekolik udalosti za sebou.
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(300)
        self._reload_timer.timeout.connect(self._reload_from_disk)

        self._watcher.fileChanged.connect(lambda _p: self._reload_timer.start())
        self._watcher.directoryChanged.connect(lambda _p: self._reload_timer.start())

    def _reload_from_disk(self) -> None:
        # Po atomickem prepsani uz watcher starou cestu nesleduje - vratit.
        path = str(self.store.path)
        if self.store.path.exists() and path not in self._watcher.files():
            self._watcher.addPath(path)

        # Rozepsany text ma prednost: dokud bezi autosave, cizi zmenu ignorujeme,
        # jinak by uzivateli zmizelo pod rukama to, co prave pise.
        if self._save_timer.isActive():
            return
        if not self.store.reload_if_changed():
            return

        keep = self._current.id if self._current else None
        self._current = self.store.get(keep) if keep else None
        self.refresh_list(select_id=keep)
        self.statusBar().showMessage("Načteno ze souboru (změnil widget)", 2000)

    # ------------------------------------------------------------------ UI --

    def _build_actions(self) -> None:
        self.action_new = QAction("Nová poznámka", self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.triggered.connect(self.new_note)

        self.action_delete = QAction("Smazat", self)
        self.action_delete.setShortcut(QKeySequence("Ctrl+Delete"))
        self.action_delete.triggered.connect(self.delete_current)

        self.action_quit = QAction("Ukončit", self)
        self.action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_quit.triggered.connect(self.close)

        self.action_about = QAction("O aplikaci", self)
        self.action_about.triggered.connect(self._show_about)

        menu = self.menuBar().addMenu("&Soubor")
        menu.addAction(self.action_new)
        menu.addAction(self.action_delete)
        menu.addSeparator()
        menu.addAction(self.action_quit)
        self.menuBar().addMenu("&Nápověda").addAction(self.action_about)

        toolbar = QToolBar("Hlavní panel", self)
        toolbar.setMovable(False)
        toolbar.addAction(self.action_new)
        toolbar.addAction(self.action_delete)
        self.addToolBar(toolbar)

    def _build_ui(self) -> None:
        self.listwidget = QListWidget()
        self.listwidget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.listwidget.setAlternatingRowColors(True)
        self.listwidget.currentItemChanged.connect(self._on_selection_changed)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Název poznámky")
        self.title_edit.setClearButtonEnabled(True)
        self.title_edit.textChanged.connect(self._on_edited)

        self.body_edit = QPlainTextEdit()
        self.body_edit.setPlaceholderText("Text poznámky…")
        self.body_edit.textChanged.connect(self._on_edited)

        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(8, 8, 8, 8)
        editor_layout.addWidget(self.title_edit)
        editor_layout.addWidget(self.body_edit)

        empty = QLabel("Žádná poznámka.\nVytvoř novou přes Ctrl+N.")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setEnabled(False)

        self.stack = QStackedWidget()
        self.stack.addWidget(empty)  # index 0
        self.stack.addWidget(editor)  # index 1

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.listwidget)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 700])

        self.setCentralWidget(splitter)

    # --------------------------------------------------------------- Logika --

    def refresh_list(self, select_id: str | None = None) -> None:
        """Prekresli seznam poznamek a obnovi vyber."""
        self._loading = True
        self.listwidget.clear()

        for note in self.store.notes:
            item = QListWidgetItem(note.title or "Bez názvu")
            item.setData(NOTE_ID_ROLE, note.id)
            item.setToolTip(_relative_time(note.updated))
            self.listwidget.addItem(item)

        self._loading = False

        target = select_id or (self._current.id if self._current else None)
        row = self._row_for(target) if target else 0
        if 0 <= row < self.listwidget.count():
            self.listwidget.setCurrentRow(row)
        else:
            self._show_note(None)

    def _row_for(self, note_id: str) -> int:
        for row in range(self.listwidget.count()):
            if self.listwidget.item(row).data(NOTE_ID_ROLE) == note_id:
                return row
        return -1

    def _show_note(self, note: Note | None) -> None:
        self.flush_pending_save()
        self._loading = True
        self._current = note

        if note is None:
            self.stack.setCurrentIndex(0)
            self.action_delete.setEnabled(False)
            self.title_edit.clear()
            self.body_edit.clear()
        else:
            self.stack.setCurrentIndex(1)
            self.action_delete.setEnabled(True)
            self.title_edit.setText(note.title)
            self.body_edit.setPlainText(note.body)
            self.statusBar().showMessage(f"Upraveno {_relative_time(note.updated)}")

        self._loading = False

    # ---------------------------------------------------------------- Akce --

    def new_note(self) -> None:
        note = self.store.add()
        self.refresh_list(select_id=note.id)
        self.title_edit.setFocus()
        self.title_edit.selectAll()

    def delete_current(self) -> None:
        if self._current is None:
            return
        answer = QMessageBox.question(
            self,
            "Smazat poznámku",
            f"Opravdu smazat „{self._current.title}“?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._save_timer.stop()
        title = self._current.title
        self.store.delete(self._current.id)
        self._current = None
        self.refresh_list()
        self.statusBar().showMessage(f"Smazáno: {title}", 4000)

    def _on_selection_changed(self, current: QListWidgetItem | None, _previous) -> None:
        if self._loading:
            return
        if current is None:
            self._show_note(None)
            return
        self._show_note(self.store.get(current.data(NOTE_ID_ROLE)))

    def _on_edited(self, *_args) -> None:
        if self._loading or self._current is None:
            return
        self._save_timer.start()  # restart = debounce

    def _save_now(self) -> None:
        if self._current is None:
            return

        title = self.title_edit.text().strip() or "Bez názvu"
        self.store.update(self._current.id, title=title, body=self.body_edit.toPlainText())

        row = self._row_for(self._current.id)
        if row >= 0:
            item = self.listwidget.item(row)
            item.setText(title)
            item.setToolTip(_relative_time(self._current.updated))
        self.statusBar().showMessage("Uloženo", 2000)

    def flush_pending_save(self) -> None:
        """Zapise rozdelanou zmenu okamzite (pri prepnuti poznamky / zavreni okna)."""
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save_now()

    def _show_about(self) -> None:
        from . import __version__

        QMessageBox.about(
            self,
            "O aplikaci",
            f"<b>Poznámky</b> {__version__}<br><br>"
            "Jednoduchá aplikace na poznámky – sandbox projekt.<br>"
            f"Data: <code>{self.store.path}</code><br>"
            f"Qt {QGuiApplication.applicationVersion() or ''}",
        )

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self.flush_pending_save()
        super().closeEvent(event)


def _relative_time(timestamp: float) -> str:
    delta = time.time() - timestamp
    if delta < 60:
        return "před chvílí"
    if delta < 3600:
        return f"před {int(delta // 60)} min"
    if delta < 86400:
        return f"před {int(delta // 3600)} h"
    return time.strftime("%d.%m.%Y", time.localtime(timestamp))
