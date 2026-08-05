%global appid       io.github.timmy543.Notes
%global plasmoidid  io.github.timmy543.notes
%global srcname     notesapp

Name:           notes-sandbox
Version:        0.1.0
Release:        1%{?dist}
Summary:        Jednoducha aplikace na poznamky pro KDE Plasma

License:        MIT
URL:            https://github.com/timmy543/sandbox-linux
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib

Requires:       python3
Requires:       python3-pyside6

%description
Minimalisticka aplikace na poznamky napsana v Pythonu s Qt6 (PySide6).
Poznamky se ukladaji automaticky do ~/.local/share/notes-sandbox/notes.json.

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
# 1) Python modul
install -d %{buildroot}%{python3_sitelib}/%{srcname}
install -pm 0644 src/%{srcname}/*.py %{buildroot}%{python3_sitelib}/%{srcname}/

# 2) Spustitelne soubory
install -d %{buildroot}%{_bindir}

cat > %{buildroot}%{_bindir}/%{name} <<'EOF'
#!/usr/bin/python3
import sys
from notesapp.main import main
sys.exit(main())
EOF

# Pomocnik pro Plasma widget (QML neumi zapisovat soubory).
cat > %{buildroot}%{_bindir}/%{name}-store <<'EOF'
#!/usr/bin/python3
import sys
from notesapp.cli import main
sys.exit(main())
EOF

chmod 0755 %{buildroot}%{_bindir}/%{name} %{buildroot}%{_bindir}/%{name}-store

# 3) Integrace do desktopu
install -Dpm 0644 data/%{appid}.desktop   %{buildroot}%{_datadir}/applications/%{appid}.desktop
install -Dpm 0644 data/%{appid}.svg       %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
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
%{_bindir}/%{name}
%{_bindir}/%{name}-store
%{python3_sitelib}/%{srcname}/
%{_datadir}/applications/%{appid}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
%{_metainfodir}/%{appid}.metainfo.xml

%files plasmoid
%{_datadir}/plasma/plasmoids/%{plasmoidid}/

%changelog
* Wed Aug 05 2026 Jan Zeman <Pepa.MCL@seznam.cz> - 0.1.0-1
- Prvni verze
