#!/usr/bin/env node
// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

/**
 * Enterprise Synapse-Hub NPM Launcher
 * ====================================
 * Dispatches CLI subcommands to the underlying Python Standard Library engine (tools/cli.py).
 * Provides cross-platform zero-install execution via `npx synapse-hub <command>`.
 */

const { spawn, execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const REPO_ROOT = path.resolve(__dirname, '..');
const CLI_PATH = path.join(REPO_ROOT, 'tools', 'cli.py');

// ANSI Color Helpers
const hasNoColor = 'NO_COLOR' in process.env;
const isDumbTerm = process.env.TERM === 'dumb';
const forceColor = ['1', 'true', 'TRUE'].includes(process.env.FORCE_COLOR);
const useColor = (Boolean(process.stdout.isTTY) || forceColor) && !hasNoColor && !isDumbTerm;
const RED = useColor ? '\x1b[91m' : '';
const GREEN = useColor ? '\x1b[92m' : '';
const YELLOW = useColor ? '\x1b[93m' : '';
const CYAN = useColor ? '\x1b[96m' : '';
const BOLD = useColor ? '\x1b[1m' : '';
const RESET = useColor ? '\x1b[0m' : '';

/**
 * Resolves the available Python 3 executable across Windows, macOS, and Linux.
 */
function resolvePython() {
  const candidates = process.platform === 'win32'
    ? ['python', 'py', 'python3']
    : ['python3', 'python'];

  for (const cmd of candidates) {
    try {
      const output = execFileSync(cmd, ['--version'], { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
      const match = output.match(/Python\s+(\d+)\.(\d+)/i);
      if (match) {
        const major = parseInt(match[1], 10);
        const minor = parseInt(match[2], 10);
        if (major > 3 || (major === 3 && minor >= 10)) {
          return { command: cmd, version: output };
        }
      }
    } catch {
      // Continue checking next candidate in path
      continue;
    }
  }
  return null;
}

const PASSTHROUGH_CMDS = ['sh', 'bash', '/bin/sh', '/bin/bash', 'cat'];

function main() {
  const firstArg = process.argv[2];
  if (firstArg && (PASSTHROUGH_CMDS.includes(firstArg) || (path.isAbsolute(firstArg) && fs.existsSync(firstArg)))) {
    const child = spawn(firstArg, process.argv.slice(3), {
      stdio: 'inherit',
      env: process.env
    });
    child.on('error', (err) => {
      console.error(`\n${BOLD}${RED}[ERROR] Failed to execute ${firstArg}:${RESET}`, err.message);
      process.exit(1);
    });
    child.on('exit', (code, signal) => {
      if (signal) {
        process.kill(process.pid, signal);
      } else {
        process.exit(code ?? 0);
      }
    });
    process.on('SIGINT', () => child.kill('SIGINT'));
    process.on('SIGTERM', () => child.kill('SIGTERM'));
    return;
  }

  const python = resolvePython();

  if (!python) {
    if (process.argv.includes('--first-run')) {
      process.exit(0);
    }
    console.error(`\n${BOLD}${RED}[ERROR] Python 3.10+ is required to execute synapse-hub tools.${RESET}`);
    console.error(`[LỖI] Cần cài đặt Python 3.10+ để thực thi các công cụ Synapse Hub.`);
    console.error(`Neither ${CYAN}python3${RESET} nor ${CYAN}python${RESET} (>= 3.10) was found on your PATH.`);
    console.error(`Không tìm thấy ${CYAN}python3${RESET} hoặc ${CYAN}python${RESET} (>= 3.10) trong biến môi trường PATH.`);
    console.error(`👉 Please install Python from: ${BOLD}https://www.python.org/downloads/${RESET}`);
    console.error(`👉 Tải và cài đặt Python tại: ${BOLD}https://www.python.org/downloads/${RESET}\n`);
    process.exit(1);
  }

  if (!fs.existsSync(CLI_PATH)) {
    console.error(`\n${BOLD}${RED}[ERROR] Core CLI engine not found at: ${CLI_PATH}${RESET}\n`);
    process.exit(1);
  }

  let args;
  if (process.argv[2] === '--py') {
    args = process.argv.slice(3);
  } else {
    args = [CLI_PATH, ...process.argv.slice(2)];
  }

  // Spawn child Python process inheriting standard IO
  const child = spawn(python.command, args, {
    stdio: 'inherit',
    env: { ...process.env, AGENT_QA_INVOKER: 'npm' }
  });

  child.on('error', (err) => {
    console.error(`\n${BOLD}${RED}[ERROR] Failed to start synapse-hub CLI:${RESET}`, err.message);
    process.exit(1);
  });

  child.on('exit', (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
    } else {
      process.exit(code ?? 0);
    }
  });

  process.on('SIGINT', () => child.kill('SIGINT'));
  process.on('SIGTERM', () => child.kill('SIGTERM'));
}

if (require.main === module) {
  main();
} else {
  module.exports = { resolvePython, PASSTHROUGH_CMDS };
}
