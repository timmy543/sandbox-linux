/*
 * Plasma 6 widget - poznamky na plose.
 *
 * QML neumi zapisovat soubory, takze veskere IO jde pres pomocne CLI
 * `notes-sandbox-store` spoustene Plasma5Support executable datasource.
 * Diky tomu widget sdili stejny notes.json s desktopovou aplikaci.
 */

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.plasma.plasmoid
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    readonly property string helper: "notes-sandbox-store"

    property var notes: []
    property int currentIndex: 0
    property bool populating: false
    property bool helperMissing: false

    readonly property var currentNote:
        (currentIndex >= 0 && currentIndex < notes.length) ? notes[currentIndex] : null

    preferredRepresentation: fullRepresentation

    Layout.minimumWidth: Kirigami.Units.gridUnit * 11
    Layout.minimumHeight: Kirigami.Units.gridUnit * 8
    Layout.preferredWidth: Kirigami.Units.gridUnit * 18
    Layout.preferredHeight: Kirigami.Units.gridUnit * 14

    Component.onCompleted: load()

    // ------------------------------------------------------------ Data --

    P5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []

        property var callbacks: ({})

        function run(command, callback) {
            if (callback !== undefined) {
                callbacks[command] = callback;
            }
            connectSource(command);
        }

        onNewData: function (source, data) {
            disconnectSource(source);
            const callback = callbacks[source];
            if (callback !== undefined) {
                delete callbacks[source];
                callback(data["exit code"], data["stdout"], data["stderr"]);
            }
        }
    }

    function applyResult(exitCode, stdout, keepId) {
        if (exitCode !== 0) {
            // 127 = prikaz nenalezen -> balicek notes-sandbox neni nainstalovany
            helperMissing = (exitCode === 127);
            return;
        }
        helperMissing = false;

        let parsed;
        try {
            parsed = JSON.parse(stdout);
        } catch (e) {
            return;
        }

        populating = true;
        notes = parsed.notes || [];

        let target = 0;
        const wanted = keepId !== undefined ? keepId : (currentNote ? currentNote.id : "");
        for (let i = 0; i < notes.length; ++i) {
            if (notes[i].id === wanted) {
                target = i;
                break;
            }
        }
        currentIndex = notes.length > 0 ? target : -1;
        editor.text = currentNote ? currentNote.body : "";
        populating = false;
    }

    function load() {
        executable.run(helper + " load", function (code, out) {
            applyResult(code, out, plasmoid.configuration.noteId);
        });
    }

    function newNote() {
        saveTimer.stop();
        executable.run(helper + " new", function (code, out) {
            if (code !== 0) {
                helperMissing = (code === 127);
                return;
            }
            let created;
            try {
                created = JSON.parse(out);
            } catch (e) {
                return;
            }
            applyResult(code, out, created.note ? created.note.id : undefined);
            rememberCurrent();
            editor.forceActiveFocus();
        });
    }

    function saveNow() {
        saveTimer.stop();
        if (!currentNote) {
            return;
        }
        const payload = {
            id: currentNote.id,
            title: currentNote.title,
            body: editor.text
        };
        const keepId = currentNote.id;
        executable.run(helper + " save " + Qt.btoa(JSON.stringify(payload)), function (code, out) {
            if (code === 0) {
                // Neprekreslujeme editor - uzivatel muze mezitim psat dal.
                try {
                    notes = JSON.parse(out).notes || [];
                } catch (e) {
                    return;
                }
                for (let i = 0; i < notes.length; ++i) {
                    if (notes[i].id === keepId) {
                        currentIndex = i;
                        break;
                    }
                }
            }
        });
    }

    function deleteCurrent() {
        if (!currentNote) {
            return;
        }
        saveTimer.stop();
        executable.run(helper + " delete " + currentNote.id, function (code, out) {
            applyResult(code, out, "");
            rememberCurrent();
        });
    }

    function step(delta) {
        if (notes.length === 0) {
            return;
        }
        saveNow();
        populating = true;
        currentIndex = (currentIndex + delta + notes.length) % notes.length;
        editor.text = currentNote ? currentNote.body : "";
        populating = false;
        rememberCurrent();
    }

    function rememberCurrent() {
        plasmoid.configuration.noteId = currentNote ? currentNote.id : "";
    }

    Timer {
        id: saveTimer
        interval: 800
        onTriggered: root.saveNow()
    }

    // Zachyti zmeny provedene v desktopove aplikaci. Pri psani se neprovadi,
    // aby uzivateli nepodrazila rozepsany text.
    Timer {
        interval: 15000
        running: true
        repeat: true
        onTriggered: {
            if (!editor.activeFocus && !saveTimer.running) {
                root.load();
            }
        }
    }

    // -------------------------------------------------------------- UI --

    fullRepresentation: ColumnLayout {
        spacing: Kirigami.Units.smallSpacing

        RowLayout {
            Layout.fillWidth: true
            spacing: 0

            PlasmaComponents.ToolButton {
                icon.name: "go-previous-symbolic"
                enabled: root.notes.length > 1
                onClicked: root.step(-1)
                PlasmaComponents.ToolTip.text: i18n("Předchozí poznámka")
                PlasmaComponents.ToolTip.visible: hovered
            }

            PlasmaComponents.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: root.currentNote
                      ? root.currentNote.title + "  (" + (root.currentIndex + 1) + "/" + root.notes.length + ")"
                      : ""
            }

            PlasmaComponents.ToolButton {
                icon.name: "go-next-symbolic"
                enabled: root.notes.length > 1
                onClicked: root.step(1)
                PlasmaComponents.ToolTip.text: i18n("Další poznámka")
                PlasmaComponents.ToolTip.visible: hovered
            }

            PlasmaComponents.ToolButton {
                icon.name: "list-add-symbolic"
                onClicked: root.newNote()
                PlasmaComponents.ToolTip.text: i18n("Nová poznámka")
                PlasmaComponents.ToolTip.visible: hovered
            }

            PlasmaComponents.ToolButton {
                icon.name: "edit-delete-symbolic"
                enabled: root.currentNote !== null
                onClicked: root.deleteCurrent()
                PlasmaComponents.ToolTip.text: i18n("Smazat poznámku")
                PlasmaComponents.ToolTip.visible: hovered
            }
        }

        QQC2.ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.currentNote !== null && !root.helperMissing

            PlasmaComponents.TextArea {
                id: editor
                wrapMode: TextEdit.Wrap
                placeholderText: i18n("Text poznámky…")
                font.pointSize: plasmoid.configuration.fontSize > 0
                                ? plasmoid.configuration.fontSize
                                : Kirigami.Theme.defaultFont.pointSize

                onTextChanged: {
                    if (!root.populating && root.currentNote) {
                        saveTimer.restart();
                    }
                }
                onActiveFocusChanged: {
                    if (!activeFocus && saveTimer.running) {
                        root.saveNow();
                    }
                }
            }
        }

        PlasmaExtras.PlaceholderMessage {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.helperMissing
            iconName: "dialog-error"
            text: i18n("Chybí notes-sandbox")
            explanation: i18n("Nainstaluj balíček:  sudo dnf install notes-sandbox")
        }

        PlasmaExtras.PlaceholderMessage {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !root.helperMissing && root.currentNote === null
            iconName: "document-new"
            text: i18n("Žádná poznámka")

            helpfulAction: Kirigami.Action {
                icon.name: "list-add-symbolic"
                text: i18n("Nová poznámka")
                onTriggered: root.newNote()
            }
        }
    }
}
