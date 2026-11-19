#!/usr/bin/env node
// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

/**
 * Enterprise Synapse-Hub NPM Launcher
 * ====================================
 * Dispatches CLI subcommands to the underlying Python Standard Library engine (tools/core/cli.py).
 * Provides cross-platform zero-install execution via `npx @teevee98/synapse-hub <command>`.
 */

const { spawn, execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const REPO_ROOT = path.resolve(__dirname, '..');
const CLI_PATH = fs.existsSync(path.join(REPO_ROOT, 'tools', 'core', 'cli.py'))
  ? path.join(REPO_ROOT, 'tools', 'core', 'cli.py')
  : path.join(REPO_ROOT, 'tools', 'cli.py');

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

const ALLOWLIST_SUBCOMMANDS = new Set([
  // Core & diagnostics
  'help', 'set-lang', 'lang', 'init', 'init-config', 'new', 'playground', 'version', 'setup', 'doctor', 'uninstall',
  'welcome', 'ui', 'dashboard', 'clean', 'update', 'check-version', 'sync-rules',
  // Verification, linting & quality
  'verify', 'verify-manual', 'lint', 'auto-heal', 'heal-pr', 'heal', 'mutate', 'shard', 'jira',
  'trend', 'flaky', 'canary', 'watch', 'pinpoint-failure', 'ci-hook', 'slow-tests',
  'heap-snapshot', 'analyze', 'debt', 'harvest-debt', 'harvest', 'adaptive-rules',
  'rule-harvester', 'slice', 'context-slice', 'review', 'code-review', 'safety-check',
  'contract-drift', 'skillspector', 'skills', 'profiles', 'list-skills', 'verify-author',
  'wcag-audit', 'rules-router', 'route-rules', 'impact', 'review-spec', 'drift-check',
  'trace-data-flow', 'distill', 'gherkin', 'transpile', 'omni-scan', 'report-bug',
  'mock-shield', 'visual-mask', 'migrate', 'decouple-config', 'fuzz-api', 'som',
  'export-postman', 'generate-jmx', 'analyze-jtl', 'export-excel', 'correlate-telemetry',
  'analyze-newman', 'tokens', 'lookup-tc', 'lookup-xpath', 'generate-tc', 'api-matrix',
  'canvas-diff', 'validate-groovy', 'mcp', 'mcp-serve', 'mcp-excel', 'mcp-docx', 'release',
  'publish', 'cvss-calc', 'asvs-check', 'vpat-export', 'compliance-matrix', 'cldr-validate',
  'ai-gateway', 'etl-pipeline', 'tmmi-assess', 'pre-push', 'pentest-recon', 'db-sandbox',
  'tms-sync', 'sec-ledger', 'secret-vault', 'slides-gen', 'cov-budget', 'pairwise-gen',
  'humanize-test', 'fsm-enforce', 'vcr-record', 'assert-optimizer', 'sec-scan', 'sbom-gen',
  'task-memory', 'memory-os', 'break-ui', 'tot-explore', 'diag-runner', 'allure-report',
  'report-summary', 'host-interop', 'qa-broker', 'event-stream', 'qa-observer',
  'qa-benchmark', 'agentless-repair', 'reflexion', 'web-agent-gym', 'chaos-mesh',
  'contract-matrix', 'distill-skills', 'probe-flow', 'pre-commit-guard', 'worktree-sync',
  'interview', 'mobile-guard', 'observability', 'payload-firewall', 'repo-map',
  'skill-guard', 'adaptive-ci', 'validate-skills', 'lint-docs', 'benchmark-swarm',
  'benchmark-runner', 'traffic-generator', 'tool-catalog', 'project-state', 'sandbox-exec',
  'fuzz-payloads', 'ast-cache'
]);

/**
 * Spawns a child process inheriting standard IO with signal forwarding.
 */
function runChildProcess(command, args, envExtra = {}) {
  const child = spawn(command, args, {
    stdio: 'inherit',
    env: { ...process.env, ...envExtra }
  });

  child.on('error', (err) => {
    console.error(`\n${BOLD}${RED}[ERROR] Failed to execute ${command}:${RESET}`, err.message);
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
  return child;
}

function main() {
  const firstArg = process.argv[2];

  // Block arbitrary absolute path execution and dangerous shell bypasses
  if (firstArg && path.isAbsolute(firstArg)) {
    console.error(`\n${BOLD}${RED}[SECURITY ERROR] Direct absolute binary execution is prohibited: ${firstArg}${RESET}\n`);
    process.exit(1);
  }

  // Enforce subcommand allowlist if argument is not a flag
  if (firstArg && !firstArg.startsWith('-') && !ALLOWLIST_SUBCOMMANDS.has(firstArg)) {
    console.error(`\n${BOLD}${RED}[ERROR] Unknown or unauthorized subcommand: '${firstArg}'${RESET}`);
    console.error(`Direct execution of arbitrary commands is prohibited for security.`);
    console.error(`Run ${CYAN}synapse --help${RESET} to view all authorized subcommands.\n`);
    process.exit(1);
  }

  const python = resolvePython();

  if (!python) {
    console.error(`\n${BOLD}${RED}[ERROR] Python 3.10+ is required to execute synapse-hub tools.${RESET}`);
    console.error(`[LỖI] Cần cài đặt Python 3.10+ để thực thi các công cụ Synapse Hub.`);
    console.error(`Neither ${CYAN}python3${RESET} nor ${CYAN}python${RESET} (>= 3.10) was found on your PATH.`);
    console.error(`Không tìm thấy ${CYAN}python3${RESET} hoặc ${CYAN}python${RESET} (>= 3.10) trong biến môi trường PATH.\n`);
    console.error(`${BOLD}${CYAN}👉 Quick 1-Command Installation for your OS:${RESET}`);
    if (process.platform === 'darwin') {
      console.error(`   macOS:   ${BOLD}brew install python@3.11${RESET}`);
    } else if (process.platform === 'win32') {
      console.error(`   Windows: ${BOLD}winget install Python.Python.3.11${RESET}`);
    } else {
      console.error(`   Linux:   ${BOLD}sudo apt update && sudo apt install -y python3${RESET}`);
    }
    console.error(`   Or download installer directly: ${BOLD}https://www.python.org/downloads/${RESET}\n`);
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

  runChildProcess(python.command, args, { AGENT_QA_INVOKER: 'npm' });
}

if (require.main === module) {
  main();
} else {
  module.exports = { resolvePython, ALLOWLIST_SUBCOMMANDS, runChildProcess };
}
