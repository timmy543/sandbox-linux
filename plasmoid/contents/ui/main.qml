/*
 * Plasma 6 widget - poznamky na plose.
 *
 * QML neumi zapisovat soubory, takze veskere IO jde pres pomocne CLI
 * `stickynotes-store` spoustene Plasma5Support executable datasource.
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

    readonly property string helper: "stickynotes-store"

    property var notes: []
    property int currentIndex: 0
    // Id poznamky, ktera ma byt vybrana az dobehne rozdelane ukladani.
    // Odpovedi z helperu mohou dorazit mimo poradi, proto vzdy plati posledni cil.
    property string pendingSelection: ""
    property bool populating: false
    property bool helperMissing: false

    // fullRepresentation je Component, takze ma vlastni scope - id deklarovana
    // uvnitr nej nejsou z rootu videt (jinak "ReferenceError: editor is not
    // defined" pri kazdem pristupu). TextArea se sem proto zaregistruje sama.
    // Muze byt null: full representation vznika az kdyz ji Plasma potrebuje.
    property Item editorItem: null

    // Telo prave zobrazene poznamky. Bere se z editoru, dokud existuje;
    // po jeho zniceni (sbaleny widget) plati posledni znama hodnota.
    readonly property string editorBody: editorItem ? editorItem.text : lastBody
    property string lastBody: ""

    // Totez pro nazev poznamky (stejny scope problem jako u editorItem).
    property Item titleItem: null
    readonly property string editorTitle: titleItem ? titleItem.text : lastTitle
    property string lastTitle: ""

    // Ma uzivatel neco rozepsaneho oproti tomu, co je ulozene? Pouziva se na
    // trech mistech (refresh, listovani, nova poznamka) - musi zahrnovat nazev
    // i telo, jinak by se zmena nazvu bud ztratila, nebo prepsala cizi zapis.
    readonly property bool dirty: currentNote
        ? (editorBody !== currentNote.body || editorTitle !== currentNote.title)
        : false

    // Pocet zapisu, ktere uz odesly helperu a jeste se nevratily. Refresh se po
    // tu dobu musi drzet zpatky - jinak by nacetl stav souboru z doby PRED
    // zapisem a vratil uzivateli text, ktery prave napsal.
    property int savesInFlight: 0

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

    // Zapis do editoru pres `populating`, aby se nespustil autosave. Editor
    // nemusi existovat (sbaleny widget) - hodnotu si pak drzi lastBody a
    // TextArea si ji vyzvedne pri svem vzniku.
    function setEditorText(text) {
        lastBody = text;
        if (!editorItem || editorItem.text === text) {
            // Stejny obsah = nesahat na TextArea. Prirazeni by uzivateli
            // preskocilo kurzor na konec, i kdyz se realne nic nemeni.
            return;
        }
        const before = populating;
        populating = true;
        editorItem.text = text;
        populating = before;
    }

    function setTitleText(text) {
        lastTitle = text;
        if (!titleItem || titleItem.text === text) {
            return;
        }
        const before = populating;
        populating = true;
        titleItem.text = text;
        populating = before;
    }

    function applyResult(exitCode, stdout, keepId) {
        if (exitCode !== 0) {
            // 127 = prikaz nenalezen -> balicek stickynotes-timmy543 neni nainstalovany
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
        setEditorText(currentNote ? currentNote.body : "");
        setTitleText(currentNote ? currentNote.title : "");
        pendingSelection = currentNote ? currentNote.id : "";
        populating = false;
    }

    function noteById(id) {
        for (let i = 0; i < notes.length; ++i) {
            if (notes[i].id === id) {
                return notes[i];
            }
        }
        return null;
    }

    function load() {
        executable.run(helper + " load", function (code, out) {
            applyResult(code, out, plasmoid.configuration.noteId);
        });
    }

    function newNote() {
        // Rozepsany text nesmi spadnout pod stul: saveTimer.stop() by ho zahodil,
        // kdyz uzivatel klikne na "nova" driv, nez debounce (1 s) dobehne.
        // Helper dela read-modify-write, takze soubezny save a "new" si nevadi.
        if (dirty) {
            saveNow();
        }
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
            // Focus na nazev, ne na telo - stejne jako v desktopove aplikaci je
            // prvni krok u nove poznamky pojmenovat ji.
            if (titleItem) {
                titleItem.forceActiveFocus();
                titleItem.selectAll();
            } else if (editorItem) {
                editorItem.forceActiveFocus();
            }
        });
    }

    function saveNow(noteId, noteTitle, noteBody, keepId) {
        saveTimer.stop();
        if (!noteId && !currentNote) {
            return;
        }
        const payload = {
            id: noteId || currentNote.id,
            title: noteTitle !== undefined ? noteTitle : editorTitle,
            body: noteBody !== undefined ? noteBody : editorBody
        };
        // Stav, ze ktereho tahle uprava vychazi (posledni nacteni ze souboru).
        // Helper podle nej pozna, jestli do stejneho pole mezitim nezapsala
        // aplikace - pak nas zapis toho pole zahodi misto prepsani.
        const base = noteById(payload.id);
        if (base) {
            payload.base = { title: base.title, body: base.body };
        }
        pendingSelection = keepId !== undefined
                           ? keepId
                           : (currentNote ? currentNote.id : payload.id);
        savesInFlight++;
        executable.run(helper + " save " + Qt.btoa(JSON.stringify(payload)), function (code, out) {
            savesInFlight = Math.max(0, savesInFlight - 1);
            if (code === 0) {
                // Neprekreslujeme editor - uzivatel muze mezitim psat dal.
                let fresh;
                try {
                    fresh = JSON.parse(out).notes || [];
                } catch (e) {
                    return;
                }
                // Helper po ulozeni preskladá seznam podle `updated`, takze
                // currentIndex musime dohledat znovu. Bereme aktualni cil, ne ten
                // zachyceny pri odeslani - odpovedi mohou dorazit mimo poradi.
                let target = -1;
                for (let i = 0; i < fresh.length; ++i) {
                    if (fresh[i].id === pendingSelection) {
                        target = i;
                        break;
                    }
                }
                if (target < 0) {
                    return;
                }
                notes = fresh;
                currentIndex = target;
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
        const oldNote = currentNote;
        const oldBody = editorBody;
        const oldTitle = editorTitle;
        const wasDirty = dirty;
        saveTimer.stop();
        const nextIndex = (currentIndex + delta + notes.length) % notes.length;
        currentIndex = nextIndex;
        setEditorText(currentNote ? currentNote.body : "");
        setTitleText(currentNote ? currentNote.title : "");
        pendingSelection = currentNote ? currentNote.id : "";
        rememberCurrent();

        // Ulozit JEN kdyz uzivatel opravdu psal. Pouhe prolistovani nesmi nic
        // zapisovat: widget ma data az 10 s stara (viz refresh timer nize), takze
        // bezduvodny zapis by prepsal to, co mezitim ulozila desktopova aplikace.
        // Zaroven tim odpada round-trip pri kazdem prepnuti, ktery drive rozhazoval
        // cislovani "x/y".
        if (oldNote && wasDirty) {
            saveNow(oldNote.id, oldTitle, oldBody, currentNote ? currentNote.id : oldNote.id);
        }
    }

    function rememberCurrent() {
        plasmoid.configuration.noteId = currentNote ? currentNote.id : "";
    }

    Timer {
        id: saveTimer
        interval: 1000
        onTriggered: root.saveNow()
    }

    // Zachyti zmeny provedene v desktopove aplikaci. Pri psani se neprovadi,
    // aby uzivateli nepodrazila rozepsany text.
    Timer {
        interval: 10000
        running: true
        repeat: true
        onTriggered: {
            // Rozdelany zapis (ceka na debounce nebo uz bezi) - pockat na dalsi kolo,
            // jinak by nam soubor vratil stav z doby pred nim.
            if (saveTimer.running || root.savesInFlight > 0) {
                return;
            }
            // Neulozene zmeny v editoru. Drive se tu testoval activeFocus, jenze
            // ten muze na plose zustat drzeny i kdyz uzivatel pracuje v aplikaci,
            // a refresh se pak nespustil vubec. Rozhoduje skutecny stav textu.
            if (root.dirty) {
                return;
            }
            root.load();
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

            // Nazev je editovatelny primo tady, aby nezabiral dalsi radek -
            // widget na plose mi vertikalniho mista nazbyt.
            PlasmaComponents.TextField {
                id: titleField
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                enabled: root.currentNote !== null
                placeholderText: i18n("Název poznámky")
                // Bez ramecku, aby to v panelu porad pusobilo jako popisek.
                background: null

                Component.onCompleted: {
                    root.populating = true;
                    text = root.lastTitle;
                    root.populating = false;
                    root.titleItem = this;
                }
                Component.onDestruction: {
                    root.lastTitle = text;
                    root.titleItem = null;
                }

                onTextChanged: {
                    if (!root.populating && root.currentNote) {
                        root.lastTitle = text;
                        saveTimer.restart();
                    }
                }
                // Enter = potvrdit a hned zapsat, at uzivatel neceka na debounce.
                onAccepted: root.saveNow()
                onActiveFocusChanged: {
                    if (!activeFocus && saveTimer.running) {
                        root.saveNow();
                    }
                }
            }

            PlasmaComponents.Label {
                visible: root.notes.length > 0
                opacity: 0.7
                text: (root.currentIndex + 1) + "/" + root.notes.length
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

                // Root na `editor` nedosahne (jiny scope), musime se prihlasit
                // sami. Zaroven prevezmeme text nactený, nez editor existoval.
                Component.onCompleted: {
                    root.populating = true;
                    text = root.lastBody;
                    root.populating = false;
                    root.editorItem = this;
                }
                Component.onDestruction: {
                    root.lastBody = text;
                    root.editorItem = null;
                }

                onTextChanged: {
                    if (!root.populating && root.currentNote) {
                        root.lastBody = text;
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
            text: i18n("Chybí stickynotes-timmy543")
            explanation: i18n("Nainstaluj balíček:  sudo dnf install stickynotes-timmy543")
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
