# notes-sandbox

Jednoduchá aplikace na poznámky pro **Nobara / Fedora + KDE Plasma**.
Python 3 + Qt6 (PySide6), automatické ukládání, RPM balíček distribuovaný přes GitHub Pages.

Sandbox projekt na vyzkoušení celého řetězce: *kód → RPM → vlastní dnf repo → `dnf install`*.

## Jak to funguje

| Vrstva | Soubor |
|---|---|
| Ukládání dat (nezávislé na GUI) | [src/notesapp/storage.py](src/notesapp/storage.py) |
| Okno a UI logika | [src/notesapp/window.py](src/notesapp/window.py) |
| Start aplikace | [src/notesapp/main.py](src/notesapp/main.py) |
| RPM předpis | [packaging/notes-sandbox.spec](packaging/notes-sandbox.spec) |
| Lokální build | [packaging/build-rpm.sh](packaging/build-rpm.sh) |
| CI + publikace repa | [.github/workflows/rpm.yml](.github/workflows/rpm.yml) |

Poznámky se ukládají do `~/.local/share/notes-sandbox/notes.json`.

## 1. Spuštění z kódu (vývoj)

```bash
sudo dnf install python3-pyside6
git clone https://github.com/timmy543/sandbox-linux.git
cd sandbox-linux
PYTHONPATH=src python3 -m notesapp.main
```

### Vývoj na Windows

Qt je multiplatformní, takže si aplikaci můžeš zkoušet i na Windows (jen bude mít
windowsí vzhled místo Plasmy). Balení do RPM samozřejmě jen na Linuxu.

```powershell
.\run-windows.ps1
```

Skript si při prvním spuštění sám vytvoří `.venv` a nainstaluje PySide6.
Data se ukládají do `%LOCALAPPDATA%\notes-sandbox\notes.json`.

## 2. Postavení RPM lokálně

```bash
sudo dnf install rpm-build rpmdevtools desktop-file-utils libappstream-glib
./packaging/build-rpm.sh
sudo dnf install ~/rpmbuild/RPMS/noarch/notes-sandbox-0.1.0-1*.noarch.rpm
```

Pak se aplikace objeví v nabídce Plasmy jako **Poznámky**.

### Odinstalace

```bash
sudo dnf remove notes-sandbox            # odejde i widget (má na aplikaci Requires)
sudo dnf remove notes-sandbox-plasmoid   # jen widget, aplikace zůstane
```

Dvě věci, které odinstalace neudělá:

- **Poznámky nesmaže** — `~/.local/share/notes-sandbox/` je v domovském adresáři,
  RPM databáze o něm neví. Smazat ručně: `rm -rf ~/.local/share/notes-sandbox`.
- **Widget nesundá z plochy.** Pokud ho tam necháš viset, Plasma po odinstalaci ukáže
  chybové políčko „widget není k dispozici", protože v konfiguraci plochy zůstal zápis.
  Nejdřív ho sundej z plochy (pravý klik → Odebrat), pak odinstaluj.

## 3. Vlastní dnf repo na GitHubu

Jednorázově v repozitáři: **Settings → Pages → Source: GitHub Actions**.

Workflow po každém pushi do `main`:
1. postaví RPM ve Fedora kontejneru,
2. vygeneruje `createrepo_c` metadata,
3. publikuje je na `https://timmy543.github.io/sandbox-linux/rpm/`.

Na Nobaře pak stačí:

```bash
sudo dnf config-manager --add-repo https://timmy543.github.io/sandbox-linux/notes-sandbox.repo
sudo dnf install notes-sandbox
```

Nová verze = zvednout `Version:` ve spec souboru + `version` v `pyproject.toml`, pushnout,
a uživatelům přijde přes `dnf upgrade`. Tag `v0.2.0` navíc vytvoří GitHub Release s RPM.

### Co z toho vznikne za balíčky

Jeden spec soubor vyrobí **dva balíčky**:

| Balíček | Obsah | Kde se projeví |
|---|---|---|
| `notes-sandbox` | aplikace + `notes-sandbox-store` | ikona **Poznámky** v nabídce Plasmy |
| `notes-sandbox-plasmoid` | QML widget | *Přidat widgety* → **Poznámky** |

Widget nemá `.desktop` soubor, takže se v nabídce aplikací **neobjeví** — je jen v seznamu
widgetů. V nabídce tedy uvidíš jednu položku, i když jsou balíčky dva.

Ve spec souboru je `Supplements: (notes-sandbox and plasma-workspace)`, což znamená:
na systému s Plasmou si `dnf install notes-sandbox` přitáhne widget automaticky.
Na GNOME nebo serveru ne. Nechceš-li ho, `dnf install notes-sandbox --setopt=install_weak_deps=False`.

### Discover vs. dnf

Workflow generuje do metadat repozitáře dvě věci:

- **`createrepo_c`** — bez toho `dnf` repozitář vůbec nenačte.
- **`appstream-builder`** — katalog aplikací. Bez něj `dnf install notes-sandbox` funguje,
  ale v **Discoveru** (grafický správce balíčků) by se aplikace neukázala mezi aplikacemi,
  protože Discover čte právě AppStream katalog, ne seznam balíčků. Proto se do repodata
  vkládá `modifyrepo_c --mdtype=appstream`.

Zdroj těch údajů (název, ikona, popis, screenshoty) je
[data/io.github.timmy543.Notes.metainfo.xml](data/io.github.timmy543.Notes.metainfo.xml).

> Repo je bez GPG podpisu (`gpgcheck=0`) — pro sandbox v pohodě. Pro veřejnou distribuci
> se klíč vygeneruje přes `gpg --gen-key`, balíčky se podepíšou `rpmsign --addsign`
> a veřejný klíč se vystaví vedle repa.

## Kam se ukládají data

Poznámky jsou v jednom JSON souboru, žádná databáze:

| Systém | Cesta |
|---|---|
| Linux | `~/.local/share/notes-sandbox/notes.json` (respektuje `XDG_DATA_HOME`) |
| Windows | `%LOCALAPPDATA%\notes-sandbox\notes.json` |

Formát:

```json
{
  "version": 1,
  "notes": [
    { "id": "a3f…", "title": "Nákup", "body": "mléko\nchleba", "updated": 1770000000.0 }
  ]
}
```

Zápis je atomický (nejdřív `notes.json.tmp`, pak přejmenování), takže pád aplikace
uprostřed ukládání soubor nerozbije. Kdyby se JSON přesto poškodil, aplikace ho odloží
jako `notes.json.broken` a začne s prázdným seznamem místo aby data smazala.

Odinstalace RPM data **nemaže** — jsou v domovském adresáři, ne v `/usr`.

## Widget na plochu (Plasma 6)

Kromě aplikace je v repu i **plasmoid** — widget, který si přilepíš na plochu.
Sdílí stejný `notes.json`, takže co napíšeš ve widgetu, uvidíš v aplikaci a naopak.

```
plasmoid/
├─ metadata.json              popis widgetu pro Plasmu
└─ contents/
   ├─ ui/main.qml             samotný widget
   ├─ ui/configGeneral.qml    nastavení (velikost písma)
   └─ config/main.xml         definice uložených voleb
```

Instalace pro vývoj (bez RPM):

```bash
./plasmoid/dev-install.sh
```

Pak pravý klik na plochu → **Přidat widgety** → *Poznámky* → přetáhnout na plochu.
Z RPM se instaluje podbalíčkem `sudo dnf install notes-sandbox-plasmoid`.

### Proč QML a ne Python

Plasma umí načíst jen QML balíček — cizí proces jako svou součást spustit nedokáže,
a Python bindingy pro plasmoidy skončily s Plasma 4. QML navíc neumí zapisovat soubory.

Widget proto veškeré IO deleguje na CLI [`notes-sandbox-store`](src/notesapp/cli.py),
které spouští přes `Plasma5Support` executable datasource:

| Příkaz | Co dělá |
|---|---|
| `notes-sandbox-store load` | vypíše všechny poznámky jako JSON |
| `notes-sandbox-store new` | vytvoří poznámku |
| `notes-sandbox-store save <base64>` | uloží `{id,title,body}` |
| `notes-sandbox-store delete <id>` | smaže poznámku |

Data jdou jako **base64** (`Qt.btoa()` v QML), aby v shellu nevznikaly problémy
s uvozovkami a diakritikou. Zápis je stejně jako v aplikaci debouncovaný (800 ms).
Widget se navíc každých 15 s podívá, jestli soubor nezměnila aplikace — ale jen když
zrovna nepíšeš, aby ti nepodrazil rozepsaný text.

## Kam se instaluje

```
/usr/bin/notes-sandbox              spustitelný soubor
/usr/bin/notes-sandbox-store        helper pro widget
/usr/share/notes-sandbox/notesapp/  Python modul
/usr/share/applications/…           položka v nabídce
/usr/share/icons/hicolor/…          ikona (SVG + PNG 48/64/128)
/usr/share/plasma/plasmoids/…       widget
```

Modul **záměrně nejde** do `%{python3_sitelib}`. Ta cesta obsahuje verzi Pythonu
(`/usr/lib/python3.14/site-packages`) a vyhodnotí se **při buildu** — balíček postavený
na Fedoře 42 (Python 3.13) by na Fedoře 43 (Python 3.14) vlastní modul nenašel a spadl
by na `ModuleNotFoundError`. Nobara je rolling distribuce, takže se pod tím bude Python
měnit. Verzově nezávislá cesta + `sys.path.insert()` ve spouštěči znamená, že jeden
balíček funguje napříč vydáními.

PNG ikony jsou tam kvůli AppStreamu — `appstream-builder` samotné SVG neuzná a aplikace
by se neobjevila v Discoveru.

## Identita aplikace

App-id `io.github.timmy543.Notes` je zároveň názvem souborů v [data/](data/) a hodnotou
`Icon=` v `.desktop`. Když ho měníš, přejmenuj i ty soubory — jinak KDE nespáruje
ikonu s oknem a v panelu bude šedý čtvereček.

## Alternativy k RPM

- **COPR** – build service Fedory zdarma, uděláš `copr build` a repo hostuje Red Hat.
- **Flatpak** – běží kdekoliv nezávisle na distribuci, sandboxované, jde publikovat na Flathub.
- **AppImage** – jeden spustitelný soubor bez instalace.
