#!/bin/bash
# Builds "Code Diagram Server.app": a windowless app that runs server.py.
# It exists so macOS privacy settings can give the diagrams folder access to this app only, not to all of Python.
set -euo pipefail

SERVER_DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Applications/Code Diagram Server.app"
PORT=7878

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"

cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleIdentifier</key><string>com.paddymac.code-diagram-server</string>
  <key>CFBundleName</key><string>Code Diagram Server</string>
  <key>CFBundleExecutable</key><string>run</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSUIElement</key><true/>
</dict>
</plist>
EOF

# A compiled launcher, not a shell script: macOS privacy checks the app's main program,
# and a script would be checked as /bin/bash instead of this app.
# It keeps the server running, restarting it if it stops (as launchd KeepAlive did before).
LAUNCHER_SOURCE="$(mktemp -d)/run.c"
cat > "$LAUNCHER_SOURCE" <<EOF
#include <fcntl.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    for (;;) {
        pid_t server = fork();
        if (server == 0) {
            int log = open("$HOME/Library/Logs/code-diagram.log", O_WRONLY | O_CREAT | O_APPEND, 0644);
            dup2(log, 1);
            dup2(log, 2);
            execl("/usr/bin/python3", "python3", "$SERVER_DIR/server.py", "$PORT", (char *)0);
            _exit(127);
        }
        waitpid(server, 0, 0);
        sleep(5);
    }
}
EOF
clang -O2 -o "$APP/Contents/MacOS/run" "$LAUNCHER_SOURCE"

codesign --force --sign - --identifier com.paddymac.code-diagram-server "$APP"
echo "Built $APP"
