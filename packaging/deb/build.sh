#!/bin/sh
# Build scripturesstudio_<version>_all.deb
# Usage: packaging/deb/build.sh
set -eu

cd "$(dirname "$0")/../.."
REPO_ROOT="$(pwd)"
VERSION="0.$(git rev-list --count HEAD)"
sed -i "s/^Version: .*/Version: $VERSION/" packaging/deb/control

PKG_DIR="$REPO_ROOT/debian-pkg"
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/DEBIAN" "$PKG_DIR/usr/share/scripturesstudio/templates" \
	"$PKG_DIR/usr/share/scripturesstudio/wavesurfer" "$PKG_DIR/usr/bin" \
	"$PKG_DIR/usr/share/doc/scripturesstudio"
cp packaging/deb/control "$PKG_DIR/DEBIAN/control"
cp ScripturesStudio.py Asset.py Audio.py AudioBible.py Image.py Overlay.py Video.py tls.py \
   audio.js styles.css logo.png \
   "$PKG_DIR/usr/share/scripturesstudio/"
cp -r templates/. "$PKG_DIR/usr/share/scripturesstudio/templates/"
cp -r wavesurfer/. "$PKG_DIR/usr/share/scripturesstudio/wavesurfer/"
chmod +x "$PKG_DIR/usr/share/scripturesstudio/ScripturesStudio.py"
ln -s ../share/scripturesstudio/ScripturesStudio.py "$PKG_DIR/usr/bin/scripturesstudio"
cp GPL-3 "$PKG_DIR/usr/share/doc/scripturesstudio/copyright"
dpkg-deb --build --root-owner-group "$PKG_DIR" "scripturesstudio_${VERSION}_all.deb"
rm -rf "$PKG_DIR"
echo "Built scripturesstudio_${VERSION}_all.deb"
