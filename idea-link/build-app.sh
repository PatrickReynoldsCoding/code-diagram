#!/bin/bash
# Builds "IntelliJ Line Opener.app": a windowless app that handles idealine:// links by running open_link.py.
# An AppleScript app, because a link click reaches the app as an Apple Event ("open location").
set -euo pipefail

LINK_DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Applications/IntelliJ Line Opener.app"
LSREGISTER=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister

rm -rf "$APP"
osacompile -o "$APP" -e "on open location linkUrl
  do shell script \"/usr/bin/python3 -I '$LINK_DIR/open_link.py' \" & quoted form of linkUrl & \" >> \$HOME/Library/Logs/idealine.log 2>&1\"
end open location"

PLIST="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.paddymac.intellij-line-opener" "$PLIST" 2>/dev/null ||
  /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string com.paddymac.intellij-line-opener" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes array" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0 dict" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0:CFBundleURLName string IntelliJ line link" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes array" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string idealine" "$PLIST"

codesign --force --deep --sign - "$APP"
"$LSREGISTER" -f "$APP"
echo "Built $APP"
