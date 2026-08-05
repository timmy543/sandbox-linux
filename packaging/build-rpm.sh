#!/usr/bin/env bash
# Postavi RPM balicek lokalne. Spoustet z korene repozitare:  ./packaging/build-rpm.sh
set -euo pipefail

NAME="notes-sandbox"
VERSION="$(sed -n 's/^Version:[[:space:]]*//p' packaging/${NAME}.spec)"
TOPDIR="$(rpm --eval '%{_topdir}')"

echo ">> ${NAME} ${VERSION}"

# Potrebne nastroje (jednorazove):
#   sudo dnf install rpm-build rpmdevtools desktop-file-utils libappstream-glib createrepo_c
command -v rpmbuild >/dev/null || { echo "chybi rpm-build: sudo dnf install rpm-build rpmdevtools"; exit 1; }

mkdir -p "${TOPDIR}"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Zdrojovy tarball musi mit korenovy adresar <name>-<version>/ kvuli %autosetup.
STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT
mkdir -p "${STAGE}/${NAME}-${VERSION}"
cp -r src data plasmoid README.md LICENSE "${STAGE}/${NAME}-${VERSION}/"
tar -czf "${TOPDIR}/SOURCES/${NAME}-${VERSION}.tar.gz" -C "${STAGE}" "${NAME}-${VERSION}"

# REL_SUFFIX nastavuje CI (napr. ".42") aby kazdy build mel vyssi NEVR nez
# predchozi. Lokalne se necha prazdny a Release zustane "1".
RPMBUILD_ARGS=()
if [[ -n "${REL_SUFFIX:-}" ]]; then
    echo ">> release suffix: ${REL_SUFFIX}"
    RPMBUILD_ARGS+=(--define "rel_suffix ${REL_SUFFIX}")
fi

rpmbuild -ba "${RPMBUILD_ARGS[@]}" "packaging/${NAME}.spec"

echo
echo ">> Hotovo:"
find "${TOPDIR}/RPMS" -name "${NAME}-${VERSION}*.rpm"
echo
echo ">> Instalace:  sudo dnf install ${TOPDIR}/RPMS/noarch/${NAME}-${VERSION}-*.noarch.rpm"
