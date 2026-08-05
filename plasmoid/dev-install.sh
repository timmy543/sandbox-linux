#!/usr/bin/env bash
# Rychla instalace widgetu bez RPM - pro vyvoj na Nobare.
#   ./plasmoid/dev-install.sh          nainstaluje / aktualizuje
#   ./plasmoid/dev-install.sh remove   odinstaluje
set -euo pipefail

ID="io.github.timmy543.stickynotes"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "remove" ]]; then
    kpackagetool6 --type Plasma/Applet --remove "${ID}"
    echo ">> odinstalovano"
    exit 0
fi

if kpackagetool6 --type Plasma/Applet --list 2>/dev/null | grep -qx "${ID}"; then
    kpackagetool6 --type Plasma/Applet --upgrade "${DIR}"
else
    kpackagetool6 --type Plasma/Applet --install "${DIR}"
fi

echo
echo ">> Widget nainstalovan do ~/.local/share/plasma/plasmoids/${ID}"
echo ">> Pridani na plochu: pravy klik na plochu -> Pridat widgety -> 'Poznamky'"
echo
echo ">> Po zmene QML staci znovu spustit tenhle skript a pak:"
echo "   systemctl --user restart plasma-plasmashell   (Wayland)"
