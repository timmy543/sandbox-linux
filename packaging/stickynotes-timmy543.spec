%global appid       io.github.timmy543.StickyNotes
%global plasmoidid  io.github.timmy543.stickynotes
%global srcname     stickynotes

# Nazvy prikazu jsou zamerne kratsi nez %%{name}: v balicku je "-timmy543" jen
# kvuli unikatnosti v repu, uzivatel ho v terminalu psat nemusi. Helper musi
# presne sedet s konstantou `helper` v plasmoid/contents/ui/main.qml.
%global cmd         stickynotes
%global storecmd    %{cmd}-store

# Modul zamerne NEJDE do %%{python3_sitelib}. Ta cesta obsahuje verzi Pythonu
# (/usr/lib/python3.14/site-packages) a vyhodnoti se pri buildu - balicek
# postaveny na Fedore 42 by pak na Fedore 43 nenasel vlastni modul.
# Nobara je rolling, takze se pod tim Python bude menit. Verzove nezavisla
# cesta znamena, ze jeden balicek funguje napric vydanimi.
# Pozn.: nazev je tu napsany natvrdo - %%global se expanduje hned pri definici,
# takze %%{name} jeste neni znamy (nastavuje ho az tag Name: nize).
%global appdir      %{_datadir}/stickynotes-timmy543

Name:           stickynotes-timmy543
Version:        0.1.0
# rel_suffix dodava CI (cislo behu workflow), aby kazdy build z main mel vyssi
# NEVR nez ten predchozi - jinak dnf upgrade hlasi "Neni co delat" i kdyz je
# v repu cerstve postaveny balicek. Lokalni build bez definice zustava na "1".
Release:        1%{?rel_suffix}%{?dist}
Summary:        Jednoducha aplikace na poznamky pro KDE Plasma

License:        MIT
URL:            https://github.com/timmy543/sandbox-linux
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib
# rsvg-convert: AppStream katalog vyzaduje rastrove ikony, samotne SVG nestaci.
BuildRequires:  librsvg2-tools

Requires:       python3
Requires:       python3-pyside6

%description
Minimalisticka aplikace na poznamky napsana v Pythonu s Qt6 (PySide6).
Poznamky se ukladaji automaticky do ~/.local/share/stickynotes-timmy543/notes.json.

%package plasmoid
Summary:        Widget na plochu pro KDE Plasma
Requires:       %{name} = %{version}-%{release}
Requires:       plasma-workspace
Supplements:    (%{name} and plasma-workspace)

%description plasmoid
Plasma 6 widget, ktery zobrazuje poznamky primo na plose. Sdili stejna data
s desktopovou aplikaci - obe strany ctou a zapisuji stejny notes.json.

%prep
%autosetup

%build
# Cisty Python, neni co kompilovat.

%install
# 1) Python modul (verzove nezavisla cesta, viz %%global appdir nahore)
install -d %{buildroot}%{appdir}/%{srcname}
install -pm 0644 src/%{srcname}/*.py %{buildroot}%{appdir}/%{srcname}/
%py_byte_compile %{__python3} %{buildroot}%{appdir}

# 2) Spustitelne soubory
install -d %{buildroot}%{_bindir}

cat > %{buildroot}%{_bindir}/%{cmd} <<EOF
#!/usr/bin/python3
import sys
sys.path.insert(0, "%{appdir}")
from stickynotes.main import main
sys.exit(main())
EOF

# Pomocnik pro Plasma widget (QML neumi zapisovat soubory).
cat > %{buildroot}%{_bindir}/%{storecmd} <<EOF
#!/usr/bin/python3
import sys
sys.path.insert(0, "%{appdir}")
from stickynotes.cli import main
sys.exit(main())
EOF

chmod 0755 %{buildroot}%{_bindir}/%{cmd} %{buildroot}%{_bindir}/%{storecmd}

# 3) Integrace do desktopu
install -Dpm 0644 data/%{appid}.desktop   %{buildroot}%{_datadir}/applications/%{appid}.desktop
install -Dpm 0644 data/%{appid}.svg       %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg

# PNG varianty - bez nich appstream-builder aplikaci zaradi mezi 'failed'
# a v Discoveru se neobjevi. Plasma sama by si vystacila se SVG.
for size in 48 64 128; do
    install -d %{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps
    rsvg-convert -w ${size} -h ${size} \
        -o %{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/%{appid}.png \
        data/%{appid}.svg
done
install -Dpm 0644 data/%{appid}.metainfo.xml %{buildroot}%{_metainfodir}/%{appid}.metainfo.xml

# 4) Plasma widget
install -d %{buildroot}%{_datadir}/plasma/plasmoids/%{plasmoidid}
cp -a plasmoid/metadata.json plasmoid/contents %{buildroot}%{_datadir}/plasma/plasmoids/%{plasmoidid}/
find %{buildroot}%{_datadir}/plasma/plasmoids/%{plasmoidid} -type f -exec chmod 0644 {} +

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{appid}.desktop
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/%{appid}.metainfo.xml

%files
%license LICENSE
%doc README.md
%{_bindir}/%{cmd}
%{_bindir}/%{storecmd}
%{appdir}/
%{_datadir}/applications/%{appid}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
%{_datadir}/icons/hicolor/*/apps/%{appid}.png
%{_metainfodir}/%{appid}.metainfo.xml

%files plasmoid
%{_datadir}/plasma/plasmoids/%{plasmoidid}/

%changelog
* Wed Aug 05 2026 Jan Zeman <Pepa.MCL@seznam.cz> - 0.1.0-1
- Prvni verze
