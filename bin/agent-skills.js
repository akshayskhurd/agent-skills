#!/usr/bin/env node
/**
 * Cross-platform CLI runner for Agent Skills Toolkit.
 * Dispatches to install.sh on POSIX or install.py on Windows.
 */
const { spawn } = require("child_process");
const path = require("path");

const isWin = process.platform === "win32";
const rootDir = path.resolve(__dirname, "..");

let command;
let args;

if (isWin) {
  command = process.env.PYTHON || "python";
  args = [path.join(rootDir, "install.py"), ...process.argv.slice(2)];
} else {
  command = path.join(rootDir, "install.sh");
  args = process.argv.slice(2);
}

const child = spawn(command, args, {
  stdio: "inherit",
  shell: isWin,
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
