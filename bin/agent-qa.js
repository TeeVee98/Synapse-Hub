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
  'aci', 'adaptive-rules', 'agentless', 'agentless-patch', 'ai-eval', 'all-pairs',
  'allure', 'analyze', 'analyze-jtl', 'analyze-newman', 'api-matrix',
  'architecture-diagram', 'assert-opt', 'assertion-optimizer', 'ast-cache', 'ast-map',
  'asvs', 'auto-heal', 'auto-reflexion', 'bench-tool', 'benchmark-runner',
  'benchmark-swarm', 'break-ui', 'browsergym', 'cache-ast', 'cache-proxy', 'canary',
  'canvas-diff', 'catalog', 'chaos', 'chaos-probe', 'check-host', 'check-skills',
  'check-version', 'checklist', 'ci-hook', 'cldr', 'clean', 'code-review',
  'collision-guard', 'commit-guard', 'compliance', 'context-slice', 'contract-check',
  'contract-drift', 'correlate-telemetry', 'cov-report', 'cove', 'coverage',
  'cso-ledger', 'cvss', 'cyclonedx', 'dag-heal', 'dashboard', 'db-sandbox', 'debt',
  'decouple-config', 'diagram', 'distill', 'distill-skill', 'doc-lint', 'doctor',
  'drift-check', 'etl', 'event-stream', 'export-excel', 'export-postman',
  'export-slides', 'fix', 'flaky', 'flow', 'flow-probe', 'fsm', 'fsm-guard',
  'fuzz-api', 'fuzz-payloads', 'gen-catalog', 'generate-allure', 'generate-jmx',
  'generate-tc', 'gherkin', 'git-worktree', 'grid', 'guard-push', 'gym-eval',
  'har-to-k6', 'harvest', 'harvest-debt', 'harvest-journey', 'harvest-plan', 'heal',
  'heal-pr', 'heap-leak', 'help', 'history', 'host-interop', 'hub-push', 'humanize',
  'humanize-lint', 'impact', 'init', 'init-config', 'interview', 'interview-story',
  'jira', 'jira-sync', 'knowledge-lake', 'lang', 'leak-check', 'lint', 'lint-docs',
  'list-skills', 'lookup-tc', 'lookup-xpath', 'mcp', 'mcp-docx', 'mcp-excel',
  'mcp-serve', 'memory-leak', 'memory-os', 'migrate', 'mobile-guard',
  'mobile-sentinel', 'mock-shield', 'mutate', 'new', 'observability', 'observer',
  'omni-scan', 'onboard', 'otel-tester', 'pairwise', 'payloads', 'payment-sim',
  'payment-simulator', 'pentest', 'pentest-guard', 'perf-runner', 'pinpoint-failure',
  'pre-commit', 'pre-push', 'probe-flow', 'profiles', 'project-state', 'pstate',
  'publish', 'push-hub', 'qa-bench', 'qa-broker', 'qa-events', 'qa-memory',
  'reflexion', 'release', 'repo-map', 'report-bug', 'report-summary', 'rev-sandbox',
  'review', 'review-spec', 'route-rules', 'rule-harvester', 'rules-router',
  'safety-check', 'sandbox', 'sandbox-db', 'sbom', 'scaffold-tc', 'schedule',
  'scope-guard', 'sec-scan', 'security-ledger', 'security-scan', 'set-lang', 'setup',
  'shard', 'skill-distill', 'skill-guard', 'skill-vault', 'skills', 'skillspector',
  'slice', 'slides', 'slow-profiler', 'slow-tests', 'slowest-tests', 'som',
  'swarm-bench', 'swarm-broker', 'swarm-contract', 'swe-aci', 'synapse-observer',
  'sync-jira', 'sync-rules', 'sync-schemas', 'task-mem', 'task-memory',
  'test-summary', 'tmmi', 'tms-bridge', 'tms-sync', 'tokens', 'tool-catalog',
  'tot-exploratory', 'tot-test', 'trace-data-flow', 'traffic-convert',
  'traffic-converter', 'transpile', 'trend', 'trends', 'ui', 'ui-chaos', 'uninstall',
  'update', 'validate-groovy', 'validate-skills', 'vault', 'vcr', 'verify',
  'verify-author', 'verify-manual', 'version', 'visual-mask', 'vpat', 'watch',
  'wcag-audit', 'welcome', 'worktree'
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

const ALLOWED_TOP_LEVEL_FLAGS = new Set(['-h', '--help', '-v', '--version', '-V']);

function main() {
  const firstArg = process.argv[2];

  // Block arbitrary absolute path execution and dangerous shell bypasses
  if (firstArg && path.isAbsolute(firstArg)) {
    console.error(`\n${BOLD}${RED}[SECURITY ERROR] Direct absolute binary execution is prohibited: ${firstArg}${RESET}\n`);
    process.exit(1);
  }

  // Enforce strict flag allowlist (blocks --py and arbitrary interpreter flag pass-through)
  if (firstArg && firstArg.startsWith('-') && !ALLOWED_TOP_LEVEL_FLAGS.has(firstArg)) {
    console.error(`\n${BOLD}${RED}[SECURITY ERROR] Unauthorized top-level flag: '${firstArg}'${RESET}`);
    console.error(`Direct Python interpreter pass-through and arbitrary flags are prohibited.`);
    console.error(`Run ${CYAN}synapse --help${RESET} to view all authorized subcommands.\n`);
    process.exit(1);
  }

  // Enforce subcommand allowlist if argument is not an allowed flag
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

  const args = [CLI_PATH, ...process.argv.slice(2)];

  runChildProcess(python.command, args, { AGENT_QA_INVOKER: 'npm' });
}

if (require.main === module) {
  main();
} else {
  module.exports = { resolvePython, ALLOWLIST_SUBCOMMANDS, ALLOWED_TOP_LEVEL_FLAGS, runChildProcess };
}
