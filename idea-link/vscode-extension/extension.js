// Opens vscode://paddymac.idealine/<absolute path>:<line> in IntelliJ.
// VS Code's markdown preview opens other link schemes (idea://, idealine://) as a VS Code editor and fails,
// and http links open a browser tab. A vscode:// link for this extension stays inside VS Code and comes here.
const vscode = require("vscode");
const { execFile } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const CODE_ROOT = path.join(os.homedir(), "repos");

// The idea:// URL for an existing file under CODE_ROOT, or undefined.
function ideaUrlFor(fileAndLine) {
  const match = /^(.*?)(?::(\d+))?$/.exec(fileAndLine);
  const codeFile = path.resolve(match[1]);
  const line = match[2] || "1";
  const insideCodeRoot = codeFile.startsWith(CODE_ROOT + path.sep);
  if (!insideCodeRoot || !fs.existsSync(codeFile) || !fs.statSync(codeFile).isFile()) return undefined;
  return `idea://open?file=${encodeURIComponent(codeFile).replace(/%2F/g, "/")}&line=${line}`;
}

function activate(context) {
  const handler = {
    handleUri(uri) {
      const ideaUrl = ideaUrlFor(uri.path);
      if (ideaUrl === undefined) {
        vscode.window.showWarningMessage(`Not a code file under ~/repos: ${uri.path}`);
        return;
      }
      execFile("open", [ideaUrl], (error) => {
        if (error) vscode.window.showErrorMessage(`Could not open IntelliJ: ${error.message}`);
      });
    },
  };
  context.subscriptions.push(vscode.window.registerUriHandler(handler));
}

module.exports = { activate };
