#!/bin/bash
# Packs this folder as a .vsix (a zip in the VSIX layout; no vsce needed) and installs it in VS Code.
set -euo pipefail

EXTENSION_DIR="$(cd "$(dirname "$0")" && pwd)"
CODE_CLI="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
BUILD_DIR="$(mktemp -d)"
VSIX="$BUILD_DIR/idealine.vsix"

mkdir -p "$BUILD_DIR/extension"
cp "$EXTENSION_DIR/package.json" "$EXTENSION_DIR/extension.js" "$BUILD_DIR/extension/"

cat > "$BUILD_DIR/[Content_Types].xml" <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension=".json" ContentType="application/json"/>
  <Default Extension=".js" ContentType="application/javascript"/>
  <Default Extension=".vsixmanifest" ContentType="text/xml"/>
</Types>
XML

cat > "$BUILD_DIR/extension.vsixmanifest" <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Language="en-US" Id="idealine" Version="0.0.1" Publisher="paddymac"/>
    <DisplayName>IntelliJ line links</DisplayName>
    <Description xml:space="preserve">Opens vscode://paddymac.idealine links in IntelliJ.</Description>
    <Categories>Other</Categories>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.80.0"/>
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Dependencies/>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>
  </Assets>
</PackageManifest>
XML

(cd "$BUILD_DIR" && zip -qr "$VSIX" "[Content_Types].xml" extension.vsixmanifest extension)
"$CODE_CLI" --install-extension "$VSIX" --force
echo "Installed. In VS Code, run 'Developer: Reload Window' once."
