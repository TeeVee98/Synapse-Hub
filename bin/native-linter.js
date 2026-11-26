#!/usr/bin/env node
// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

/**
 * Synapse Hub Zero-Python Native Node.js Linter & Auto-Fixer Engine
 * =================================================================
 * Pure Node.js >= 18 stdlib (`fs`, `path`, `os`) static QA defect sentinel.
 * Shares rule semantics 1:1 with `tools/lint/infer_linter.py`, `tools/lint/auto_fixer.py`,
 * and `editors/vscode/src/constants.js` so Node-only environments (`node:20-alpine`,
 * Frontend laptops) execute `lint`, `fix`, `doctor`, `version`, and `help` natively
 * in < 50ms with zero Python installed.
 */

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..');

const SUPPORTED_EXTS = new Set(['.ts', '.tsx', '.js', '.jsx', '.py', '.java', '.groovy']);
const JS_TS_EXTS = new Set(['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs']);
const HASH_COMMENT_EXTS = new Set(['.py', '.sh', '.bash', '.zsh', '.yaml', '.yml', '.rb', '.r', '.toml']);

const IGNORED_DIRS = new Set([
  'tools', 'bin', 'node_modules', '.git', '.hg', '.svn', '__pycache__',
  'venv', '.venv', 'env', 'claude-ecosystem-repos', 'dist', 'build',
  '.idea', '.vscode', 'editors', '.mypy_cache', '.pytest_cache', '.ruff_cache',
  '.sandbox_snapshots', 'graphify-out', 'test-results', 'playwright-report',
  'allure-results', 'reports', 'htmlcov'
]);

const EXCLUDED_METHOD_NAMES = new Set([
  'if', 'for', 'while', 'switch', 'catch', 'else', 'try', 'finally', 'return',
  'new', 'throw', 'constructor', '__init__', '__new__', '__repr__', '__str__',
  'setUp', 'tearDown', 'beforeEach', 'afterEach', 'beforeAll', 'afterAll',
  'describe', 'context', 'suite', 'test', 'it', 'class', 'function', 'async', 'await'
]);

const GENERIC_COLLISION_METHOD_NAMES = new Set([
  'validate', 'check', 'verify', 'ensure', 'run', 'execute', 'process', 'handle', 'test', 'init', 'setup'
]);

const PLAYWRIGHT_ASYNC_MATCHERS =
  '(?:toBeVisible|toBeHidden|toHaveText|toHaveValue|toHaveCount|toBeEnabled|toBeDisabled|' +
  'toBeChecked|toHaveURL|toContainText|toHaveTitle|toHaveAttribute|toHaveClass|toHaveId|' +
  'toBeFocused|toBeEmpty|toBeAttached|toBeInViewport|toBeOK)';

const INTERACTION_KEYWORDS = [
  'click', 'select', 'save', 'delete', 'create', 'search',
  'navigate', 'open', 'fill', 'goto', 'post', 'get'
];

// ---------------------------------------------------------------------------
// 1. Lexical Comment & String Stripping (preserves line numbering)
// ---------------------------------------------------------------------------

const LEXER_JS_RE = /`(?:\\[\s\S]|[^`\\])*`|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\/\*[\s\S]*?\*\/|\/\/[^\r\n]*/g;
const LEXER_HASH_RE = /"""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|#[^\r\n]*/g;
const LEXER_CSTYLE_RE = /"""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\/\*[\s\S]*?\*\/|\/\/[^\r\n]*/g;

function stripCommentsAndStrings(sourceCode, fileExt = '.ts') {
  const ext = (fileExt || '.ts').toLowerCase();
  let pattern = LEXER_CSTYLE_RE;
  if (JS_TS_EXTS.has(ext)) {
    pattern = LEXER_JS_RE;
  } else if (HASH_COMMENT_EXTS.has(ext)) {
    pattern = LEXER_HASH_RE;
  }
  return sourceCode.replace(pattern, (match) => match.replace(/[^\r\n]/g, ' '));
}

function lineNumberAt(text, index) {
  let count = 1;
  for (let i = 0; i < index && i < text.length; i++) {
    if (text.charCodeAt(i) === 10) count++;
  }
  return count;
}

// ---------------------------------------------------------------------------
// 2. File Role Classification (1:1 parity with infer_linter.py)
// ---------------------------------------------------------------------------

function classifyFileRole(filePath, content = '') {
  const norm = filePath.replace(/\\/g, '/').toLowerCase();
  const base = path.posix.basename(norm);
  const parts = norm.split('/').slice(0, -1);

  const cfgMarkers = [
    'playwright.config', 'cypress.config', 'wdio.conf',
    'jest.config', 'karma.conf', 'conftest.py', 'tsconfig'
  ];
  if (cfgMarkers.some((cfg) => base.includes(cfg))) return 'CONFIG';
  if (parts.some((p) => p === 'config' || p === '.config')) return 'CONFIG';

  if (
    parts.some((p) => p === 'pages' || p === 'page_objects' || p === 'page-objects' || p === 'po') ||
    (parts.includes('keywords') && norm.includes('pages'))
  ) {
    return 'PAGE_OBJECT';
  }
  if (/(^|_)basepage\b/.test(base) || /[a-z0-9_]page\.(ts|js|py|groovy|java)$/.test(base)) {
    return 'PAGE_OBJECT';
  }
  if (content && (/\bclass\s+[A-Za-z0-9_]*Page\b/.test(content) || /\bextends\s+BasePage\b/.test(content))) {
    return 'PAGE_OBJECT';
  }

  const helperDirs = new Set(['fixtures', 'helpers', 'utils', 'support', 'tools', 'bin', 'benchmarks', 'benchmark']);
  if (parts.some((p) => helperDirs.has(p))) return 'HELPER';
  const helperSuffixes = [
    'helper.ts', 'helper.js', 'helper.py', 'helper.groovy',
    'utils.ts', 'utils.js', 'utils.py', 'fixture.ts', 'fixture.js'
  ];
  if (helperSuffixes.some((sfx) => base.endsWith(sfx))) return 'HELPER';

  const testSuffixes = [
    '_test.py', '.spec.ts', '.spec.js', '.test.ts', '.test.js',
    '.cy.js', '.cy.ts', '.spec.jsx', '.test.jsx', '.tc',
    'test.java', 'tests.java', 'spec.groovy'
  ];
  if (base.startsWith('test_') || testSuffixes.some((sfx) => base.endsWith(sfx))) {
    return 'TEST_SCRIPT';
  }
  if (parts.some((p) => ['tests', 'test', 'e2e', 'specs', 'cypress'].includes(p))) {
    return 'TEST_SCRIPT';
  }
  if (parts.includes('scripts')) {
    if (filePath.endsWith('.groovy') || filePath.endsWith('.tc')) return 'TEST_SCRIPT';
    return 'HELPER';
  }

  return 'TEST_SCRIPT';
}

// ---------------------------------------------------------------------------
// 3. Cross-File POM Assertion & Inheritance/Fixture Indexer
// ---------------------------------------------------------------------------

const TAUTOLOGY_RE = new RegExp(
  '(?:expect(?:\\.soft|\\.poll)?\\s*\\(\\s*(?:true|1|null|undefined)\\s*\\)\\s*\\.\\s*(?:toBe|toEqual|toBeTruthy|toBeNull|toBeUndefined)\\s*\\(\\s*(?:true|1|null|undefined)?\\s*\\)' +
  '|expect(?:\\.soft|\\.poll)?\\s*\\(\\s*([a-zA-Z0-9_]+)\\s*\\)\\s*\\.\\s*(?:toBe|toEqual)\\s*\\(\\s*\\1\\s*\\)' +
  '|\\bassert\\s+(?:True|true|1\\s*==\\s*1)\\b' +
  '|\\bassert\\s+([a-zA-Z0-9_\\.]+(?:\\([^)]*\\))?)\\s*==\\s*\\2\\b' +
  '|\\bassert\\s+(?:len\\s*\\([^)]*\\)|[a-zA-Z0-9_\\.]+\\.(?:length|size\\(\\)))\\s*(?:>=\\s*0|>\\s*-(?:1|0))\\b' +
  '|assertEquals\\s*\\(\\s*(?:true|1|null)\\s*,\\s*(?:true|1|null)\\s*\\)' +
  '|assertTrue\\s*\\(\\s*(?:true|1)\\s*\\))',
  'gi'
);

const DIRECT_ASSERT_RE = new RegExp(
  '(?:\\bassert(?:Equals|NotEquals|True|False|Null|NotNull|That|Throws|Same|NotSame|ArrayEquals|IterableEquals|All)\\s*\\(' +
  '|\\b(?:Assert|Assertions)\\.[A-Za-z_][A-Za-z0-9_]*\\s*\\(' +
  '|\\b(?:WebUI|WS|Mobile)\\.verify[A-Za-z0-9_]*\\s*\\(' +
  '|\\bKeywordUtil\\.markFailed(?:AndStop)?\\s*\\(' +
  '|\\bassert\\.(?:equal|strictEqual|deepEqual|deepStrictEqual|ok|isTrue|isFalse|throws|rejects|match|include)\\s*\\(' +
  '|\\bpytest\\.raises\\s*\\(' +
  '|\\bself\\.assert[A-Za-z0-9_]*\\s*\\(' +
  '|\\bassert\\s+[^\\s;]' +
  '|\\.(?:should|and)\\s*\\()',
  'm'
);

function hasChainedExpectMatcher(cleanBody) {
  const re = /\bexpect(?:\.soft|\.poll)?\s*\(/g;
  let m;
  while ((m = re.exec(cleanBody)) !== null) {
    let idx = re.lastIndex;
    let depth = 1;
    while (idx < cleanBody.length && depth > 0) {
      const ch = cleanBody[idx];
      if (ch === '(') depth++;
      else if (ch === ')') depth--;
      idx++;
    }
    if (depth !== 0) continue;
    while (idx < cleanBody.length && /\s/.test(cleanBody[idx])) idx++;
    if (idx < cleanBody.length && cleanBody[idx] === '.') {
      const rem = cleanBody.slice(idx + 1, idx + 64);
      if (/^(?:not|resolves|rejects|to[A-Z_][A-Za-z0-9_]*|[a-z][A-Za-z0-9_]*)\b/.test(rem)) {
        return true;
      }
    }
  }
  return false;
}

function bodyHasRealAssertion(cleanBody) {
  if (!cleanBody || !cleanBody.trim()) return false;
  const withoutTaut = cleanBody.replace(TAUTOLOGY_RE, ' ');
  if (hasChainedExpectMatcher(withoutTaut)) return true;
  if (DIRECT_ASSERT_RE.test(withoutTaut)) return true;
  return false;
}

function findMatchingBrace(text, openIdx) {
  let depth = 0;
  for (let i = openIdx; i < text.length; i++) {
    const ch = text[i];
    if (ch === '{') depth++;
    else if (ch === '}') {
      depth--;
      if (depth === 0) return i;
    }
  }
  return -1;
}

function extractCallsFromBody(cleanBody, selfName) {
  const calls = [];
  const seen = new Set();
  const re = /(?:\b(?:this|self|super|[A-Za-z_][A-Za-z0-9_]*)\s*\.\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(/g;
  let m;
  while ((m = re.exec(cleanBody)) !== null) {
    const callee = m[1];
    if (EXCLUDED_METHOD_NAMES.has(callee) || callee === selfName) continue;
    if (!seen.has(callee)) {
      seen.add(callee);
      calls.push(callee);
    }
  }
  return calls;
}

function discoverFiles(rootDir, maxFiles = 2000, extraIgnored = new Set()) {
  const found = [];
  if (!rootDir || !fs.existsSync(rootDir)) return found;
  const stat = fs.statSync(rootDir);
  if (stat.isFile()) {
    return [rootDir];
  }

  function walk(dir) {
    if (found.length >= maxFiles) return;
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      if (found.length >= maxFiles) return;
      const name = entry.name;
      if (entry.isDirectory()) {
        const lower = name.toLowerCase();
        if (IGNORED_DIRS.has(lower) || extraIgnored.has(lower) || name.startsWith('.')) {
          continue;
        }
        walk(path.join(dir, name));
      } else if (entry.isFile()) {
        if (name === '__init__.py' || name === 'setup.py') continue;
        const ext = path.extname(name).toLowerCase();
        if (SUPPORTED_EXTS.has(ext)) {
          found.push(path.join(dir, name));
        }
      }
    }
  }

  walk(rootDir);
  return found;
}

function buildPomAssertionIndex(rootDir, maxDepth = 3, maxFiles = 2000) {
  const files = discoverFiles(rootDir, maxFiles);
  const nodes = [];
  const classParents = {};
  const fixtureClassBindings = {};

  const classDeclRe = /\b(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?:public\s+|private\s+|protected\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*<[^>]*>)?(?:\s+extends\s+([A-Za-z_][A-Za-z0-9_]*))?/g;
  const methodRe = /^[ \t]*(?:(?:export|public|private|protected|static|async|override|final|synchronized|abstract|default)\s+)*(?:(?:function|def|void|[A-Za-z_][A-Za-z0-9_<>\[\],\s\?]*?)\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:<[^>{};]*>)?\s*\([^)]*\)\s*(?::\s*[^{;=]+?)?\s*\{/gm;
  const arrowRe = /^[ \t]*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+?)?\s*=>\s*\{/gm;

  for (const fpath of files) {
    let content;
    try {
      content = fs.readFileSync(fpath, 'utf-8');
    } catch {
      continue;
    }
    if (!content.trim()) continue;
    const ext = path.extname(fpath).toLowerCase();
    const clean = stripCommentsAndStrings(content, ext);

    // Extract Playwright test.extend<{ fixture: PageClass }>({ fixture: async ({ page }, use) => use(new PageClass(page)) })
    if (JS_TS_EXTS.has(ext) && /extend\s*(?:<|\()/.test(clean)) {
      const genericExtendRe = /\.extend\s*<\s*\{([\s\S]*?)\}\s*>/g;
      let gm;
      while ((gm = genericExtendRe.exec(clean)) !== null) {
        const body = gm[1];
        const propRe = /\b([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Z][A-Za-z0-9_]*)\b/g;
        let pm;
        while ((pm = propRe.exec(body)) !== null) {
          fixtureClassBindings[pm[1]] = pm[2];
        }
      }
      const implExtendRe = /\b([A-Za-z_][A-Za-z0-9_]*)\s*:\s*async\s*\([^)]*\)\s*=>\s*\{[\s\S]{0,240}?new\s+([A-Z][A-Za-z0-9_]*)\s*\(/g;
      let im;
      while ((im = implExtendRe.exec(clean)) !== null) {
        if (!fixtureClassBindings[im[1]]) {
          fixtureClassBindings[im[1]] = im[2];
        }
      }
    }

    if (ext === '.py') {
      // Lightweight Python class inheritance and def scanner
      const pyClassRe = /^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(([^)]*)\))?\s*:/gm;
      let cm;
      while ((cm = pyClassRe.exec(clean)) !== null) {
        const cls = cm[1];
        const bases = (cm[2] || '').split(',').map((s) => s.trim().split('.').pop()).filter((s) => /^[A-Z][A-Za-z0-9_]*$/.test(s));
        if (bases.length > 0) classParents[cls] = bases;
      }
      continue;
    }

    // Class spans & extends edges
    const classSpans = [];
    classDeclRe.lastIndex = 0;
    let cm;
    while ((cm = classDeclRe.exec(clean)) !== null) {
      const clsName = cm[1];
      const parentName = cm[2];
      if (parentName) {
        if (!classParents[clsName]) classParents[clsName] = [];
        if (!classParents[clsName].includes(parentName)) {
          classParents[clsName].push(parentName);
        }
      }
      const braceIdx = clean.indexOf('{', classDeclRe.lastIndex - 1);
      if (braceIdx === -1) continue;
      const endIdx = findMatchingBrace(clean, braceIdx);
      if (endIdx !== -1) {
        classSpans.push({ clsName, start: braceIdx, end: endIdx });
      }
    }

    function enclosingClass(pos) {
      let best = null;
      for (const sp of classSpans) {
        if (sp.start < pos && pos < sp.end) {
          const len = sp.end - sp.start;
          if (!best || len < best.len) best = { clsName: sp.clsName, len };
        }
      }
      return best ? best.clsName : null;
    }

    const seenKeys = new Set();
    for (const rx of [methodRe, arrowRe]) {
      rx.lastIndex = 0;
      let mm;
      while ((mm = rx.exec(clean)) !== null) {
        const name = mm[1];
        if (EXCLUDED_METHOD_NAMES.has(name) || name.startsWith('test_')) continue;
        const openBrace = clean.lastIndexOf('{', mm.index + mm[0].length);
        if (openBrace === -1) continue;
        const endBrace = findMatchingBrace(clean, openBrace);
        if (endBrace === -1) continue;
        const clsName = enclosingClass(mm.index);
        const key = clsName ? `${clsName}.${name}` : name;
        if (seenKeys.has(key)) continue;
        seenKeys.add(key);
        const body = clean.slice(openBrace + 1, endBrace);
        nodes.push({
          key,
          name,
          className: clsName,
          directAssert: bodyHasRealAssertion(body),
          calls: extractCallsFromBody(body, name)
        });
      }
    }
  }

  // Reverse BFS transitive assertion resolution
  const byKey = new Map();
  const keysByName = new Map();
  for (const n of nodes) {
    if (byKey.has(n.key)) {
      const existing = byKey.get(n.key);
      existing.directAssert = existing.directAssert || n.directAssert;
      existing.calls = Array.from(new Set([...existing.calls, ...n.calls]));
    } else {
      byKey.set(n.key, { ...n });
      if (!keysByName.has(n.name)) keysByName.set(n.name, []);
      keysByName.get(n.name).push(n.key);
    }
  }

  const reverseEdges = new Map();
  for (const k of byKey.keys()) reverseEdges.set(k, new Set());
  for (const [callerKey, callerNode] of byKey.entries()) {
    for (const calleeName of callerNode.calls) {
      const candidates = [];
      if (callerNode.className) {
        const sameKey = `${callerNode.className}.${calleeName}`;
        if (byKey.has(sameKey)) candidates.push(sameKey);
      }
      for (const ck of keysByName.get(calleeName) || []) {
        if (!candidates.includes(ck)) candidates.push(ck);
      }
      for (const calleeKey of candidates) {
        if (calleeKey !== callerKey) {
          reverseEdges.get(calleeKey).add(callerKey);
        }
      }
    }
  }

  const minDepth = new Map();
  const queue = [];
  for (const [key, node] of byKey.entries()) {
    if (node.directAssert) {
      minDepth.set(key, 0);
      queue.push([key, 0]);
    }
  }
  while (queue.length > 0) {
    const [curKey, depth] = queue.shift();
    if (depth >= maxDepth) continue;
    const nextDepth = depth + 1;
    for (const callerKey of reverseEdges.get(curKey) || []) {
      if (!minDepth.has(callerKey) || nextDepth < minDepth.get(callerKey)) {
        minDepth.set(callerKey, nextDepth);
        queue.push([callerKey, nextDepth]);
      }
    }
  }

  const assertionMethods = new Set();
  const qualifiedClassMethods = {};
  for (const key of minDepth.keys()) {
    const node = byKey.get(key);
    assertionMethods.add(node.name);
    if (node.className) {
      if (!qualifiedClassMethods[node.className]) qualifiedClassMethods[node.className] = new Set();
      qualifiedClassMethods[node.className].add(node.name);
    }
  }

  // Propagate asserted methods down inheritance chains (cycle-safe, max depth 5)
  for (let iter = 0; iter < 5; iter++) {
    let changed = false;
    for (const [child, parents] of Object.entries(classParents)) {
      for (const parent of parents) {
        const pMethods = qualifiedClassMethods[parent];
        if (!pMethods || pMethods.size === 0) continue;
        if (!qualifiedClassMethods[child]) qualifiedClassMethods[child] = new Set();
        for (const mName of pMethods) {
          if (!qualifiedClassMethods[child].has(mName)) {
            qualifiedClassMethods[child].add(mName);
            assertionMethods.add(mName);
            changed = true;
          }
        }
      }
    }
    if (!changed) break;
  }

  const classOwnedNames = new Set();
  for (const mSet of Object.values(qualifiedClassMethods)) {
    for (const m of mSet) classOwnedNames.add(m);
  }
  const topLevelNames = new Set(nodes.filter((n) => !n.className).map((n) => n.name));
  const unqualifiedAssertionMethods = new Set();
  for (const m of assertionMethods) {
    if (topLevelNames.has(m) || !classOwnedNames.has(m)) {
      unqualifiedAssertionMethods.add(m);
    }
  }

  return {
    assertionMethods,
    qualifiedClassMethods,
    unqualifiedAssertionMethods,
    fixtureClassBindings,
    classParents
  };
}

function extractReceiverClassBindings(cleanCode, fixtureBindings = {}) {
  const bindings = { ...fixtureBindings };
  if (!cleanCode) return bindings;

  // Track aliased imports: import { CheckoutPage as CP } from ...
  const importAliases = {};
  const aliasRe = /\b([A-Z][A-Za-z0-9_]*)\s+as\s+([A-Z][A-Za-z0-9_]*)\b/g;
  let am;
  while ((am = aliasRe.exec(cleanCode)) !== null) {
    importAliases[am[2]] = am[1];
  }
  const resolveAlias = (cls) => importAliases[cls] || cls;

  const patterns = [
    /\b([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Z][A-Za-z0-9_]*)\b/g,
    /\b(?:const|let|var|final)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*[A-Za-z_][A-Za-z0-9_<>]*\s*)?=\s*new\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/g,
    /\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Z][A-Za-z0-9_]*)\s*\(/g
  ];
  for (const re of patterns) {
    let m;
    while ((m = re.exec(cleanCode)) !== null) {
      bindings[m[1]] = resolveAlias(m[2]);
    }
  }
  const javaRe = /\b([A-Z][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*new\s+[A-Za-z_][A-Za-z0-9_]*\s*\(/g;
  let jm;
  while ((jm = javaRe.exec(cleanCode)) !== null) {
    bindings[jm[2]] = resolveAlias(jm[1]);
  }
  return bindings;
}

function receiverMatchesClassStem(receiver, className) {
  const rNorm = receiver.replace(/_/g, '').toLowerCase();
  const cNorm = className.replace(/_/g, '').toLowerCase();
  return Boolean(cNorm) && rNorm.endsWith(cNorm);
}

function matchCrossFileAssertions(cleanCode, assertionMap, fileCleanCode = null) {
  if (!assertionMap || !assertionMap.assertionMethods || assertionMap.assertionMethods.size === 0) {
    return 0;
  }
  const methods = assertionMap.assertionMethods;
  const qualifiedMap = assertionMap.qualifiedClassMethods || {};
  const unqualifiedSet = assertionMap.unqualifiedAssertionMethods || new Set();
  const bindings = extractReceiverClassBindings(
    fileCleanCode !== null ? fileCleanCode : cleanCode,
    assertionMap.fixtureClassBindings || {}
  );

  let hits = 0;
  const callRe = /(?:(\b[A-Za-z_][A-Za-z0-9_]*)\s*\.\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(/g;
  let m;
  while ((m = callRe.exec(cleanCode)) !== null) {
    const receiver = m[1];
    const callee = m[2];
    if (!methods.has(callee)) continue;

    if (Object.keys(qualifiedMap).length === 0) {
      hits++;
      continue;
    }

    const owningClasses = Object.entries(qualifiedMap)
      .filter(([, clsMethods]) => clsMethods.has(callee))
      .map(([clsName]) => clsName);

    if (!receiver) {
      if (unqualifiedSet.has(callee) || (owningClasses.length === 0 && !GENERIC_COLLISION_METHOD_NAMES.has(callee))) {
        hits++;
      }
      continue;
    }

    if (receiver === 'this' || receiver === 'self' || receiver === 'super') {
      hits++;
      continue;
    }

    const boundCls = bindings[receiver];
    if (boundCls) {
      if (qualifiedMap[boundCls] && qualifiedMap[boundCls].has(callee)) {
        hits++;
      }
      continue;
    }

    if (owningClasses.some((clsName) => receiverMatchesClassStem(receiver, clsName))) {
      hits++;
      continue;
    }

    if (!GENERIC_COLLISION_METHOD_NAMES.has(callee) && owningClasses.length > 0) {
      hits++;
    }
  }
  return hits;
}

// ---------------------------------------------------------------------------
// 4. Static Rule Scanner (1:1 parity with infer_linter.py + Clean POM XPath)
// ---------------------------------------------------------------------------

const ASSERTION_RE = new RegExp(
  '\\b(verify[A-Za-z0-9_]*|assert[A-Za-z0-9_]*|waitForToast|checkStatus|assertEquals|assertTrue|assertFalse|assertThat|expect|ensure[A-Z][A-Za-z0-9_]*Exists|check)\\b' +
  '|\\.should\\s*\\(' +
  '|\\.and\\s*\\(' +
  '|\\.(?:failure|success)\\s*\\(',
  'gm'
);

const EMPTY_CATCH_RE = new RegExp(
  '(?:catch\\s*(?:\\([^\\)]*\\))?\\s*\\{\\s*(?:(?:console|logger|log)\\.(?:log|warn|error|info)\\([^)]*\\);?\\s*|(?:const|let|var|def)?\\s*_\\s*=\\s*[^;]+;?\\s*)?\\}' +
  '|\\.catch\\s*\\(\\s*(?:\\([^)]*\\)|[a-zA-Z0-9_]+)?\\s*=>\\s*\\{\\s*(?:(?:console|logger|log)\\.(?:log|warn|error|info)\\([^)]*\\);?\\s*|(?:const|let|var|def)?\\s*_\\s*=\\s*[^;]+;?\\s*)?\\}\\s*\\)' +
  '|\\bexcept(?:\\s+[^:]*)?:\\s*(?:pass|\\.\\.\\.|_\\s*=\\s*[^#\\n;]+)(?:\\s*$|\\s*#))',
  'gm'
);

const BENIGN_TRY_CALL_RE = /^[\w.]*\.(?:reconfigure|chmod|flush|set_blocking)\s*\(/;

const UNAWAITED_EXPECT_RE = new RegExp(
  '\\bexpect(?:\\.soft|\\.poll)?\\s*\\([^;]{1,300}?\\)\\s*(?:\\.\\s*not)?\\s*\\.\\s*' + PLAYWRIGHT_ASYNC_MATCHERS + '\\s*\\(',
  'gm'
);

const MS_DELAY_RE = /\b(?:Thread\.sleep|(?:page\.)?waitForTimeout|(?:page\.)?wait_for_timeout|cy\.wait)\s*\(\s*([^)]+)\s*\)/;
const SEC_DELAY_RE = /\b(?:WebUI\.delay|time\.sleep|asyncio\.sleep)\s*\(\s*([^)]+)\s*\)/;
const RAW_XPATH_RE = /(?:page\.locator\s*\(\s*(?:'(?:\/\/|\/\*|xpath=)[^']*'|"\/\/[^"]*"|"xpath=[^"]*")\s*\)|findTestObject\s*\(\s*['"][^'"]+['"]\s*\))/;

function isBenignEmptyCatch(cleanCode, matchStart) {
  const beforeLines = cleanCode.slice(0, matchStart).split(/\r?\n/).reverse();
  const bodyLines = [];
  for (const line of beforeLines) {
    const stripped = line.trim();
    if (!stripped) continue;
    if (/^try\s*(?:[:{]|$)/.test(stripped)) {
      return bodyLines.length > 0 && bodyLines.every((bl) => BENIGN_TRY_CALL_RE.test(bl));
    }
    bodyLines.push(stripped);
  }
  return false;
}

function findDanglingExpects(cleanCode, rawLines) {
  const dangling = [];
  const re = /(?:await\s+)?\bexpect(?:\.soft|\.poll)?\s*\(/g;
  let m;
  while ((m = re.exec(cleanCode)) !== null) {
    let pos = re.lastIndex;
    let depth = 1;
    const maxScan = Math.min(cleanCode.length, pos + 1200);
    while (pos < maxScan && depth > 0) {
      const ch = cleanCode[pos];
      if (ch === '(') depth++;
      else if (ch === ')') depth--;
      else if (ch === ';' && depth > 0) break;
      pos++;
    }
    if (depth === 0) {
      const rest = cleanCode.slice(pos).trimStart();
      if (!rest.startsWith('.')) {
        const lineNo = lineNumberAt(cleanCode, m.index);
        const rawLine = (rawLines[lineNo - 1] || '').trim();
        dangling.push({ line: lineNo, raw: rawLine });
      }
    }
  }
  return dangling;
}

function hasRealAssertInText(text) {
  const asserts = [];
  ASSERTION_RE.lastIndex = 0;
  let am;
  while ((am = ASSERTION_RE.exec(text)) !== null) {
    asserts.push({ start: am.index, end: am.index + am[0].length });
  }
  const tauts = [];
  TAUTOLOGY_RE.lastIndex = 0;
  let tm;
  while ((tm = TAUTOLOGY_RE.exec(text)) !== null) {
    tauts.push({ start: tm.index, end: tm.index + tm[0].length });
  }
  return asserts.some((a) => !tauts.some((t) => t.start <= a.start && a.start < t.end));
}

function analyzeScript(filePath, opts = {}) {
  const baseRoot = opts.baseRoot || REPO_ROOT;
  const relPath = path.relative(baseRoot, filePath) || path.basename(filePath);
  const content = opts.sourceContent !== undefined
    ? opts.sourceContent
    : fs.readFileSync(filePath, 'utf-8');

  const role = classifyFileRole(filePath, content);
  if (role === 'CONFIG') {
    return {
      file: relPath,
      role,
      defects: [],
      is_clean: true,
      ast_backend: 'native_js_lexer',
      cross_file_assertions_resolved: 0
    };
  }

  const fileExt = path.extname(filePath).toLowerCase() || '.ts';
  const cleanCode = stripCommentsAndStrings(content, fileExt);
  const cleanLines = cleanCode.split(/\r?\n/);
  const rawLines = content.split(/\r?\n/);
  const defects = [];
  let crossFileResolved = 0;

  // Rule: Swallowed Exceptions
  EMPTY_CATCH_RE.lastIndex = 0;
  let ecMatch;
  while ((ecMatch = EMPTY_CATCH_RE.exec(cleanCode)) !== null) {
    if (isBenignEmptyCatch(cleanCode, ecMatch.index)) continue;
    defects.push({
      type: 'SWALLOWED_EXCEPTION',
      severity: 'CRITICAL',
      line: lineNumberAt(cleanCode, ecMatch.index),
      message: 'Empty catch block or dummy suppression (_ = err) detected. Swallowed exceptions cause false-pass test runs.'
    });
  }

  // Rule: Hard Delays
  for (let i = 0; i < cleanLines.length; i++) {
    const idx = i + 1;
    const line = cleanLines[i];
    const rawLine = (rawLines[i] || line).trim();

    const mMs = MS_DELAY_RE.exec(line);
    if (mMs) {
      const arg = mMs[1].trim();
      if (!arg.startsWith('@') && !arg.startsWith("'@") && !arg.startsWith('"@')) {
        if (/^\d+$/.test(arg)) {
          const delayVal = parseInt(arg, 10);
          if (delayVal > 0) {
            const isExcessive = delayVal >= 3000;
            defects.push({
              type: isExcessive ? 'EXCESSIVE_HARD_DELAY' : 'HARD_DELAY_ANTI_PATTERN',
              severity: (isExcessive && role === 'TEST_SCRIPT') ? 'CRITICAL' : 'WARNING',
              line: idx,
              message: `Static sleep of ${delayVal}ms found ('${rawLine}'). Replace with dynamic Smart Wait.`
            });
            continue;
          }
        } else if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(arg) && !line.trim().startsWith('cy.wait')) {
          defects.push({
            type: 'HARD_DELAY_ANTI_PATTERN',
            severity: 'WARNING',
            line: idx,
            message: `Static sleep with variable/expression '${arg}' found ('${rawLine}'). Replace with dynamic Smart Wait.`
          });
          continue;
        }
      }
    }

    const mSec = SEC_DELAY_RE.exec(line);
    if (mSec) {
      const arg = mSec[1].trim();
      const numVal = Number(arg);
      if (arg !== '' && !Number.isNaN(numVal)) {
        if (numVal > 0) {
          const delayMs = Math.floor(numVal * 1000);
          const isExcessive = delayMs >= 3000;
          defects.push({
            type: isExcessive ? 'EXCESSIVE_HARD_DELAY' : 'HARD_DELAY_ANTI_PATTERN',
            severity: (isExcessive && role === 'TEST_SCRIPT') ? 'CRITICAL' : 'WARNING',
            line: idx,
            message: `Static sleep of ${numVal}s (${delayMs}ms) found ('${rawLine}'). Replace with dynamic Smart Wait.`
          });
        }
      } else if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(arg)) {
        defects.push({
          type: 'HARD_DELAY_ANTI_PATTERN',
          severity: 'WARNING',
          line: idx,
          message: `Static sleep with variable/expression '${arg}' found ('${rawLine}'). Replace with dynamic Smart Wait.`
        });
      }
    }
  }

  // Test Script Specific Invariants
  if (role === 'TEST_SCRIPT') {
    const executableLines = cleanLines
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith('import ') && !l.startsWith('package ') && !l.startsWith('from '));

    if (executableLines.length === 0) {
      defects.push({
        type: 'EMPTY_TEST_SCRIPT',
        severity: 'CRITICAL',
        line: 1,
        message: 'Test script is empty or contains only comments/imports.'
      });
    }

    // Tautological Assertions
    for (let i = 0; i < cleanLines.length; i++) {
      TAUTOLOGY_RE.lastIndex = 0;
      if (TAUTOLOGY_RE.test(cleanLines[i])) {
        const rawLine = (rawLines[i] || cleanLines[i]).trim();
        defects.push({
          type: 'TAUTOLOGICAL_ASSERTION',
          severity: 'CRITICAL',
          line: i + 1,
          message: `Tautological assertion detected ('${rawLine}').`
        });
      }
    }

    // Dangling expect(...) without matcher
    for (const d of findDanglingExpects(cleanCode, rawLines)) {
      defects.push({
        type: 'DANGLING_ASSERTION_NO_MATCHER',
        severity: 'CRITICAL',
        line: d.line,
        message: `Dangling expect() call without matcher detected ('${d.raw}').`
      });
    }

    // Clean POM Raw XPath Selector Detection (raw lines since strings are preserved there)
    for (let i = 0; i < rawLines.length; i++) {
      const trimmedClean = (cleanLines[i] || '').trim();
      if (!trimmedClean) continue;
      if (RAW_XPATH_RE.test(rawLines[i])) {
        defects.push({
          type: 'CLEAN_POM_VIOLATION',
          severity: 'WARNING',
          line: i + 1,
          message: `Clean POM violation: raw XPath selector in test script ('${rawLines[i].trim()}'). Encapsulate locators inside a Page Class.`
        });
      }
    }

    // Unawaited Playwright Async Assertions (JS/TS)
    if (JS_TS_EXTS.has(fileExt)) {
      UNAWAITED_EXPECT_RE.lastIndex = 0;
      let um;
      while ((um = UNAWAITED_EXPECT_RE.exec(cleanCode)) !== null) {
        const prefix = cleanCode.slice(Math.max(0, um.index - 40), um.index);
        if (/\b(?:await|return)\s+$/.test(prefix)) continue;
        const surrounding = cleanCode.slice(Math.max(0, um.index - 150), um.index);
        if (surrounding.includes('Promise.all') || surrounding.includes('Promise.allSettled') || surrounding.includes('return ')) {
          continue;
        }
        const lineNo = lineNumberAt(cleanCode, um.index);
        const lineText = (rawLines[lineNo - 1] || '').trim();
        defects.push({
          type: 'UNAWAITED_ASYNC_ASSERTION',
          severity: 'CRITICAL',
          line: lineNo,
          message: `Unawaited async Playwright assertion detected: '${lineText}'.`
        });
      }
    }

    // Missing Assertions / Fake-Pass (with Cross-File POM Indexer)
    let hasRealAssert = hasRealAssertInText(cleanCode);
    const assertionMap = opts.assertionMap || null;
    if (assertionMap) {
      const hits = matchCrossFileAssertions(cleanCode, assertionMap, cleanCode);
      if (hits > 0) {
        crossFileResolved += hits;
        hasRealAssert = true;
      }
    }

    const testBlockRe = /^[ \t]*(?:(?:test|it)(?:\.(?:only|skip))?\s*\(|def\s+test_[a-zA-Z0-9_]+\s*\(|(?:@Test\s+)?(?:public\s+)?(?:void|def)\s+test[a-zA-Z0-9_]*\s*\()/gm;
    const testMatches = [];
    let tm;
    while ((tm = testBlockRe.exec(cleanCode)) !== null) {
      testMatches.push({ index: tm.index, line: lineNumberAt(cleanCode, tm.index) });
    }

    if (testMatches.length >= 2) {
      for (let i = 0; i < testMatches.length; i++) {
        const start = testMatches[i].index;
        const end = i + 1 < testMatches.length ? testMatches[i + 1].index : cleanCode.length;
        const blockCode = cleanCode.slice(start, end);
        let blockHasAssert = hasRealAssertInText(blockCode);
        if (!blockHasAssert && assertionMap) {
          const bHits = matchCrossFileAssertions(blockCode, assertionMap, cleanCode);
          if (bHits > 0) {
            crossFileResolved += bHits;
            blockHasAssert = true;
          }
        }
        const bHasInteractions = INTERACTION_KEYWORDS.some((kw) => blockCode.includes(kw));
        if (bHasInteractions && !blockHasAssert) {
          defects.push({
            type: 'FAKE_PASS_NO_ASSERTION',
            severity: 'WARNING',
            line: testMatches[i].line,
            message: `Test block starting at line ${testMatches[i].line} performs interactions but contains zero verification/assertion statements.`
          });
        }
      }
    } else {
      const hasInteractions = INTERACTION_KEYWORDS.some((kw) => cleanCode.includes(kw));
      const baseLower = path.basename(filePath).toLowerCase();
      const isExplicitTest = ['test', 'spec', 'tc-', 'tc_'].some((t) => baseLower.includes(t));
      if (hasInteractions && !hasRealAssert) {
        defects.push({
          type: 'FAKE_PASS_NO_ASSERTION',
          severity: 'WARNING',
          line: 1,
          message: 'Test script performs AUT mutations/interactions but contains zero verification/assertion statements.'
        });
      } else if (isExplicitTest && !hasRealAssert && !hasInteractions && executableLines.length > 0) {
        defects.push({
          type: 'NO_ASSERTION_IN_TEST',
          severity: 'WARNING',
          line: 1,
          message: 'Test case file contains executable logic but has no verification or assertion statements.'
        });
      }
    }
  }

  // Deduplicate by (type, line) & apply synapse-ignore comments
  const seen = new Set();
  const activeDefects = [];
  for (const d of defects) {
    const key = `${d.type}:${d.line}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const lineIdx = d.line || 1;
    const candidates = [];
    if (lineIdx >= 1 && lineIdx <= rawLines.length) candidates.push(rawLines[lineIdx - 1]);
    if (lineIdx > 1 && lineIdx - 1 <= rawLines.length) candidates.push(rawLines[lineIdx - 2]);
    let suppressed = false;
    for (const c of candidates) {
      if (c.toLowerCase().includes('synapse-ignore')) {
        const sm = /synapse-ignore:\s*([A-Za-z0-9_,\s*-]+)/i.exec(c);
        if (sm) {
          const rules = sm[1].split(',').map((r) => r.trim().toUpperCase()).filter(Boolean);
          if (rules.includes('*') || rules.includes('ALL') || rules.includes(d.type.toUpperCase())) {
            suppressed = true;
            break;
          }
        }
      }
    }
    if (!suppressed) activeDefects.push(d);
  }

  return {
    file: relPath,
    role,
    defects: activeDefects,
    is_clean: activeDefects.length === 0,
    ast_backend: 'native_js_lexer',
    cross_file_assertions_resolved: crossFileResolved
  };
}

// ---------------------------------------------------------------------------
// 5. Idempotent Auto-Fixer Engine (1:1 parity with tools/lint/auto_fixer.py)
// ---------------------------------------------------------------------------

function fixCodeContent(content, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const fixes = [];
  let updated = content;

  // 1. Dangling expect(...) without matcher (JS/TS) — run before unawaited check so single pass is idempotent
  if (JS_TS_EXTS.has(ext)) {
    const expRe = /(?:await\s+)?\bexpect(?:\.soft|\.poll)?\s*\(/g;
    let pos = 0;
    const parts = [];
    while (pos < updated.length) {
      expRe.lastIndex = pos;
      const m = expRe.exec(updated);
      if (!m) {
        parts.push(updated.slice(pos));
        break;
      }
      parts.push(updated.slice(pos, m.index));
      let curr = expRe.lastIndex;
      let depth = 1;
      while (curr < updated.length && depth > 0) {
        const ch = updated[curr];
        if (ch === '(') depth++;
        else if (ch === ')') depth--;
        else if ((ch === ';' || ch === '\n') && depth > 0) break;
        curr++;
      }
      if (depth === 0) {
        const matchedExpect = updated.slice(m.index, curr);
        const rest = updated.slice(curr);
        const restTrim = rest.trimStart();
        if (!restTrim.startsWith('.')) {
          if (restTrim.startsWith(';')) {
            const semiIdx = rest.indexOf(';');
            const ws = rest.slice(0, semiIdx);
            parts.push(`${matchedExpect}${ws}.toBeVisible();`);
            pos = curr + semiIdx + 1;
            fixes.push("Appended missing '.toBeVisible()' matcher to dangling expect() call");
            continue;
          } else {
            parts.push(`${matchedExpect}.toBeVisible()`);
            pos = curr;
            fixes.push("Appended missing '.toBeVisible()' matcher to dangling expect() call");
            continue;
          }
        }
      }
      parts.push(updated.slice(m.index, curr));
      pos = curr;
    }
    updated = parts.join('');
  }

  // 2. Unawaited async Playwright assertions (JS/TS)
  if (JS_TS_EXTS.has(ext)) {
    const asyncMatcherRe = new RegExp(`\\.${PLAYWRIGHT_ASYNC_MATCHERS}\\s*\\(`);
    const lines = updated.split(/(\r?\n)/);
    for (let i = 0; i < lines.length; i += 2) {
      const line = lines[i];
      const stripped = line.trimStart();
      if (stripped.startsWith('expect(') && !stripped.startsWith('await ') && !stripped.startsWith('return ')) {
        if (asyncMatcherRe.test(stripped)) {
          const indent = line.slice(0, line.length - stripped.length);
          lines[i] = `${indent}await ${stripped}`;
          fixes.push("Prepended missing 'await' to async Playwright assertion");
        }
      }
    }
    updated = lines.join('');
  }

  // 3. Hard delays
  if (JS_TS_EXTS.has(ext)) {
    updated = updated.replace(
      /^([ \t]*)(await\s+)?(?:page\.)?waitForTimeout\s*\(\s*\d+\s*\)\s*;?/gm,
      (_, indent, hasAwait) => {
        fixes.push("Replaced static waitForTimeout with dynamic waitForLoadState('domcontentloaded')");
        return `${indent || ''}${hasAwait ? 'await ' : ''}page.waitForLoadState('domcontentloaded');`;
      }
    );
    updated = updated.replace(
      /^([ \t]*)cy\.wait\s*\(\s*\d+\s*\)\s*;?/gm,
      (_, indent) => {
        fixes.push('Replaced cy.wait() static delay with smart assertion reminder');
        return `${indent || ''}// Synapse: Replaced cy.wait with dynamic assertion\n${indent || ''}cy.get('body').should('be.visible');`;
      }
    );
  } else if (ext === '.py') {
    updated = updated.replace(
      /^([ \t]*)page\.wait_for_timeout\s*\(\s*\d+\s*\)/gm,
      (_, indent) => {
        fixes.push("Replaced page.wait_for_timeout() with page.wait_for_load_state('domcontentloaded')");
        return `${indent || ''}page.wait_for_load_state('domcontentloaded')`;
      }
    );
    updated = updated.replace(
      /^([ \t]*)time\.sleep\s*\(\s*[\d.]+\s*\)/gm,
      (_, indent) => {
        fixes.push('Replaced time.sleep() with smart wait reminder');
        if (updated.includes('page')) {
          return `${indent || ''}page.wait_for_load_state('domcontentloaded')  # Replaced static sleep`;
        }
        return `${indent || ''}# Synapse: Replaced static sleep with dynamic smart wait`;
      }
    );
  } else if (ext === '.groovy' || ext === '.java') {
    updated = updated.replace(
      /^([ \t]*)Thread\.sleep\s*\(\s*\d+\s*\)\s*;?/gm,
      (_, indent) => {
        fixes.push('Replaced Thread.sleep() with dynamic smart wait');
        return `${indent || ''}// Synapse: Replaced static Thread.sleep with dynamic smart wait`;
      }
    );
    updated = updated.replace(
      /^([ \t]*)WebUI\.delay\s*\(\s*\d+\s*\)/gm,
      (_, indent) => {
        fixes.push('Replaced WebUI.delay() with WebUI.waitForPageLoad(10)');
        return `${indent || ''}WebUI.waitForPageLoad(10)`;
      }
    );
  }

  // 4. Swallowed exceptions
  if (JS_TS_EXTS.has(ext) || ext === '.groovy' || ext === '.java') {
    updated = updated.replace(
      /catch\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*\{\s*(?:(?:console|logger|log)\.[a-zA-Z]+\([^)]*\);?\s*|(?:const|let|var)?\s*_\s*=[^;]+;?\s*)?\}/g,
      (_, errVar) => {
        const v = errVar || 'err';
        fixes.push(`Fixed swallowed exception in catch (${v}) by re-throwing error`);
        return `catch (${v}) {\n    throw ${v};\n  }`;
      }
    );
    updated = updated.replace(
      /\.catch\s*\(\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)?\s*=>\s*\{\s*\}\s*\)/g,
      () => {
        fixes.push('Fixed swallowed Promise .catch() callback by re-throwing error');
        return '.catch((err) => { throw err; })';
      }
    );
  } else if (ext === '.py') {
    updated = updated.replace(
      /^([ \t]*)except(?:\s+[A-Za-z0-9_.]+(?:\s+as\s+[A-Za-z0-9_]+)?)?\s*:\s*(?:pass|\.\.\.|_\s*=\s*[^#\n;]+)(?:\s*$|\s*#.*$)/gm,
      (_, indent) => {
        fixes.push('Fixed swallowed exception in except block by raising error');
        const ind = indent || '';
        return `${ind}except Exception as err:\n${ind}    raise err`;
      }
    );
  }

  return { content: updated, fixes };
}

function applyFileFix(filePath, dryRun = false) {
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    return { file: filePath, fixed: false, fixes: [], error: 'File not found' };
  }
  const original = fs.readFileSync(filePath, 'utf-8');
  const { content: updated, fixes } = fixCodeContent(original, filePath);
  if (fixes.length === 0 || updated === original) {
    return { file: filePath, fixed: false, fixes: [], error: null };
  }
  if (!dryRun) {
    const tmpPath = `${filePath}.synapse.tmp.${process.pid}`;
    fs.writeFileSync(tmpPath, updated, 'utf-8');
    fs.renameSync(tmpPath, filePath);
  }
  return { file: filePath, fixed: true, dry_run: dryRun, fixes, error: null };
}

// ---------------------------------------------------------------------------
// 6. Output Formatters (JSON & SARIF 2.1.0)
// ---------------------------------------------------------------------------

function formatSarif(reportData) {
  const rulesDict = {};
  const results = [];
  for (const d of reportData.all_defects || []) {
    const ruleId = d.type || 'STATIC_DEFECT';
    const level = d.severity === 'CRITICAL' ? 'error' : 'warning';
    if (!rulesDict[ruleId]) {
      rulesDict[ruleId] = {
        id: ruleId,
        shortDescription: { text: d.message || ruleId },
        defaultConfiguration: { level }
      };
    }
    results.push({
      ruleId,
      level,
      message: { text: d.message || '' },
      locations: [{
        physicalLocation: {
          artifactLocation: { uri: d.file || '' },
          region: { startLine: Math.max(1, d.line || 1) }
        }
      }]
    });
  }
  return JSON.stringify({
    $schema: 'https://json.schemastore.org/sarif-2.1.0.json',
    version: '2.1.0',
    runs: [{
      tool: {
        driver: {
          name: 'synapse-native-js-linter',
          version: getHubVersion().version,
          rules: Object.values(rulesDict)
        }
      },
      results
    }]
  }, null, 2);
}

// ---------------------------------------------------------------------------
// 7. CLI Subcommands: lint, fix, doctor, version, help
// ---------------------------------------------------------------------------

function getHubVersion() {
  let version = '4.9.0';
  let totalSkills = 57;
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'package.json'), 'utf-8'));
    if (pkg.version) version = pkg.version;
  } catch {
    // Fallback to default version
  }
  try {
    const manifest = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'skills_manifest.json'), 'utf-8'));
    if (manifest.version) version = manifest.version;
    if (manifest.totalSkills) totalSkills = manifest.totalSkills;
  } catch {
    // Fallback to default skills count
  }
  return { version, totalSkills };
}

function parseLintFlags(argv, defaultFix = false) {
  const opts = {
    target: null,
    outputPath: null,
    format: 'text',
    strict: true,
    fix: defaultFix,
    dryRun: false
  };
  for (let i = 0; i < argv.length; i++) {
    const tok = argv[i];
    if (tok === '--json') {
      opts.format = 'json';
    } else if (tok === '--sarif') {
      opts.format = 'sarif';
    } else if (tok === '--format' && i + 1 < argv.length) {
      opts.format = argv[++i];
    } else if (tok.startsWith('--format=')) {
      opts.format = tok.slice('--format='.length);
    } else if ((tok === '--out' || tok === '--output') && i + 1 < argv.length) {
      opts.outputPath = argv[++i];
    } else if ((tok === '--dir' || tok === '--repo') && i + 1 < argv.length) {
      opts.target = argv[++i];
    } else if (tok === '--fix') {
      opts.fix = true;
    } else if (tok === '--dry-run') {
      opts.dryRun = true;
    } else if (tok === '--strict') {
      opts.strict = true;
    } else if (tok === '--no-strict' || tok === '--lenient') {
      opts.strict = false;
    } else if (!tok.startsWith('-') && !opts.target) {
      opts.target = tok;
    }
  }
  return opts;
}

function resolveScanTargets(targetArg) {
  if (targetArg) {
    const resolved = path.resolve(targetArg);
    if (!fs.existsSync(resolved)) {
      return { scanDir: resolved, files: [] };
    }
    const st = fs.statSync(resolved);
    if (st.isFile()) {
      return { scanDir: path.dirname(resolved), files: [resolved] };
    }
    return { scanDir: resolved, files: discoverFiles(resolved) };
  }

  const cwd = process.cwd();
  const isHub = fs.existsSync(path.join(cwd, 'tools', 'core', 'verify_all.py'));
  const candidates = isHub
    ? ['examples', 'tests', 'test', 'e2e', 'specs', 'cypress']
    : ['Scripts', 'tests', 'test', 'e2e', 'specs', 'cypress'];
  for (const cand of candidates) {
    const candPath = path.join(cwd, cand);
    if (fs.existsSync(candPath) && fs.statSync(candPath).isDirectory()) {
      const files = discoverFiles(candPath);
      if (files.length > 0) return { scanDir: candPath, files };
    }
  }
  return { scanDir: cwd, files: [] };
}

function runLint(argv, defaultFix = false) {
  const opts = parseLintFlags(argv, defaultFix);
  const { scanDir, files } = resolveScanTargets(opts.target);

  // Auto-Fix phase if requested
  if (opts.fix || opts.dryRun) {
    let fixedFiles = 0;
    let totalFixes = 0;
    for (const f of files) {
      const res = applyFileFix(f, opts.dryRun);
      if (res.fixed) {
        fixedFiles++;
        totalFixes += res.fixes.length;
      }
    }
    if (opts.format === 'text') {
      const verb = opts.dryRun ? 'Previewed (dry-run)' : 'Applied';
      console.log(`[Synapse Native-JS] ${verb} ${totalFixes} fix(es) across ${fixedFiles} file(s).`);
    }
  }

  // Build cross-file POM assertion map
  let assertionMap = null;
  if (files.length > 0 && fs.existsSync(scanDir)) {
    let indexRoot = scanDir;
    const baseLower = path.basename(scanDir).toLowerCase();
    if (['tests', 'test', 'e2e', 'specs', 'spec', 'cypress', 'scripts'].includes(baseLower)) {
      const parentDir = path.dirname(scanDir);
      if (parentDir && parentDir !== path.dirname(parentDir) && parentDir !== REPO_ROOT) {
        indexRoot = parentDir;
      }
    }
    assertionMap = buildPomAssertionIndex(indexRoot, 3, 2000);
  }

  const results = [];
  const allDefects = [];
  let criticalCount = 0;
  let warningCount = 0;
  let cleanCount = 0;
  let totalCrossFileResolved = 0;

  for (const f of files) {
    const res = analyzeScript(f, { baseRoot: REPO_ROOT, assertionMap });
    results.push(res);
    totalCrossFileResolved += res.cross_file_assertions_resolved;
    let fileCrit = 0;
    let fileWarn = 0;
    for (const d of res.defects) {
      if (d.severity === 'CRITICAL') fileCrit++;
      else fileWarn++;
      allDefects.push({
        file: res.file,
        role: res.role,
        type: d.type,
        severity: d.severity,
        line: d.line,
        message: d.message
      });
    }
    criticalCount += fileCrit;
    warningCount += fileWarn;
    if (res.is_clean) cleanCount++;
  }

  const totalScripts = files.length;
  let healthScore = 0.0;
  if (totalScripts > 0) {
    const criticalPenalty = (criticalCount * 20.0) / totalScripts;
    const rawScore = (cleanCount / totalScripts) * 100.0 - criticalPenalty;
    healthScore = Math.max(0.0, Math.min(100.0, Math.round(rawScore * 10) / 10));
    if (cleanCount < totalScripts && healthScore >= 100.0) healthScore = 99.0;
    if (cleanCount === 0) healthScore = 0.0;
  }

  const reportData = {
    timestamp: new Date().toISOString(),
    engine: 'native-js',
    total_scripts: totalScripts,
    clean_scripts: cleanCount,
    critical_defects: criticalCount,
    warnings: warningCount,
    health_score_pct: healthScore,
    cross_file_assertions_resolved: totalCrossFileResolved,
    defect_details: results.filter((r) => !r.is_clean),
    all_defects: allDefects
  };

  if (opts.format === 'sarif') {
    const out = formatSarif(reportData);
    if (opts.outputPath) {
      fs.mkdirSync(path.dirname(path.resolve(opts.outputPath)), { recursive: true });
      fs.writeFileSync(opts.outputPath, out, 'utf-8');
    } else {
      console.log(out);
    }
    return criticalCount > 0 ? 1 : 0;
  }

  if (opts.format === 'json') {
    const out = JSON.stringify(reportData, null, 2);
    if (opts.outputPath) {
      fs.mkdirSync(path.dirname(path.resolve(opts.outputPath)), { recursive: true });
      fs.writeFileSync(opts.outputPath, out, 'utf-8');
    } else {
      console.log(out);
    }
    return criticalCount > 0 ? 1 : 0;
  }

  // Text report
  console.log(`\n[Synapse Native-JS Linter] Scanned ${totalScripts} file(s) | Clean: ${cleanCount}/${totalScripts} | Critical: ${criticalCount} | Warnings: ${warningCount} | Health: ${healthScore.toFixed(1)}%`);
  for (const d of allDefects.slice(0, 25)) {
    console.log(`  [${d.severity}] ${d.type} (${d.file}:${d.line}) - ${d.message}`);
  }
  if (allDefects.length > 25) {
    console.log(`  ... and ${allDefects.length - 25} more defect(s).`);
  }

  if (opts.strict) {
    const antiPatterns = allDefects.filter((d) => [
      'FAKE_PASS_NO_ASSERTION', 'NO_ASSERTION_IN_TEST', 'DANGLING_ASSERTION_NO_MATCHER',
      'HARD_DELAY_ANTI_PATTERN', 'EXCESSIVE_HARD_DELAY'
    ].includes(d.type)).length;
    return (criticalCount === 0 && antiPatterns === 0) ? 0 : 1;
  }
  return criticalCount === 0 ? 0 : 1;
}

function runDoctor(argv, context = {}) {
  const isJson = argv.includes('--json') || argv.includes('--format=json');
  const { version, totalSkills } = getHubVersion();
  const pythonInfo = context.pythonInfo || null;
  const report = {
    status: 'OK',
    engine: 'native-js',
    hub_version: version,
    catalog_skills: totalSkills,
    node_version: process.version,
    platform: process.platform,
    arch: process.arch,
    cpus: os.cpus().length,
    python_available: Boolean(pythonInfo),
    python_version: pythonInfo ? pythonInfo.version : null,
    native_js_commands: ['lint', 'fix', 'doctor', 'version', 'help'],
    guidance: pythonInfo
      ? 'Full Python + Native-JS hybrid runtime ready.'
      : 'Running in Zero-Python Native Node.js mode (lint, fix, doctor, version, help ready). Install Python 3.10+ for mutation testing, MCP/LSP servers, and 11-gate Hub verification.'
  };
  if (isJson) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    console.log(`Synapse Hub Doctor (Native Node.js Engine v${version})`);
    console.log(`  Node.js   : ${report.node_version} (${report.platform}/${report.arch})`);
    console.log(`  Python    : ${report.python_available ? report.python_version : 'Not found (Zero-Python Native-JS fallback active)'}`);
    console.log(`  Native OK : ${report.native_js_commands.join(', ')}`);
    console.log(`  Guidance  : ${report.guidance}`);
  }
  return 0;
}

function runVersion() {
  const { version, totalSkills } = getHubVersion();
  console.log(`Agent-QA Hub CLI v${version} (Native Node.js Engine)`);
  console.log(`Catalog: ${totalSkills} Standardized Skills | Zero-Python Native Fallback Active`);
  console.log('Created by: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>');
  console.log('License   : MIT (Attribution Required)');
  return 0;
}

function runHelp() {
  const { version } = getHubVersion();
  console.log(`Synapse Hub CLI v${version} (Zero-Python Native Node.js Engine)`);
  console.log('');
  console.log('Usage: synapse <command> [options] [--engine auto|python|native-js]');
  console.log('');
  console.log('Zero-Python Native Node.js Commands (always available without Python):');
  console.log('  lint [target] [--json|--sarif] [--fix] [--dry-run]   Static QA defect & Clean POM linter');
  console.log('  fix [target] [--dry-run]                             Auto-fix hard sleeps, unawaited expects & empty catches');
  console.log('  doctor [--json]                                      Environment & runtime diagnostics');
  console.log('  version                                              Display hub version & MIT attribution');
  console.log('  help                                                 Show this help summary');
  console.log('');
  console.log('Full Enterprise Commands (require Python 3.10+):');
  console.log('  verify, mutate, lsp, mcp, review, onboard, grid, sync-rules, ...');
  return 0;
}

function dispatchNative(subcommand, args = [], context = {}) {
  switch (subcommand) {
    case 'lint':
      return runLint(args, false);
    case 'fix':
      return runLint(args, true);
    case 'doctor':
      return runDoctor(args, context);
    case 'version':
    case '-v':
    case '--version':
    case '-V':
      return runVersion();
    case 'help':
    case '-h':
    case '--help':
    case undefined:
    case '':
      return runHelp();
    default:
      return 1;
  }
}

if (require.main === module) {
  const [subcmd, ...rest] = process.argv.slice(2);
  const code = dispatchNative(subcmd || 'help', rest, { pythonInfo: null });
  process.exit(code);
} else {
  module.exports = {
    stripCommentsAndStrings,
    classifyFileRole,
    buildPomAssertionIndex,
    analyzeScript,
    fixCodeContent,
    applyFileFix,
    formatSarif,
    runLint,
    runDoctor,
    runVersion,
    runHelp,
    dispatchNative
  };
}
