/**
 * Enterprise Browser Runtime Helper (window.__qa)
 * -------------------------------------------------------------
 * Provides advanced AI testing capabilities directly inside the live browser DOM:
 * 1. Smart Action Batching (qa.batch) - Atomic execution with pause & state preservation.
 * 2. Instant Form Audit (qa.audit) - Detects Angular/React/Vue invalid fields in 1-shot.
 * 3. Self-Healing Locator Engine (qa.heal) - Suggests resilient selectors when locators break.
 * 4. Safe Click & Overlay Bypass (qa.clickSafe) - Clears CDK/PrimeNG/Modal overlays before clicking.
 * 5. Session State Exporter/Importer (qa.exportSession / qa.importSession).
 * 6. Deterministic Sync Engine (qa.isStable / qa.waitForStable / qa.waitForNetworkIdle).
 */

(function () {
  'use strict';

  if (window.__qa && window.__qa.__version === '2.0.0') {
    return window.__qa;
  }

  // Active in-flight network request tracker
  let activeNetworkRequests = 0;
  if (!window.__qa_net_hooked) {
    window.__qa_net_hooked = true;
    if (window.fetch) {
      const origFetch = window.fetch;
      window.fetch = function () {
        activeNetworkRequests++;
        return origFetch.apply(window, arguments).finally(() => {
          activeNetworkRequests = Math.max(0, activeNetworkRequests - 1);
        });
      };
    }
    if (window.XMLHttpRequest) {
      const origOpen = XMLHttpRequest.prototype.open;
      const origSend = XMLHttpRequest.prototype.send;
      XMLHttpRequest.prototype.open = function () {
        this.addEventListener('loadend', () => {
          activeNetworkRequests = Math.max(0, activeNetworkRequests - 1);
        });
        return origOpen.apply(this, arguments);
      };
      XMLHttpRequest.prototype.send = function () {
        activeNetworkRequests++;
        return origSend.apply(this, arguments);
      };
    }
  }

  const qa = {
    __version: '2.0.0',

    /**
     * 1. Smart Action Batching
     * Runs a sequence of step functions atomically.
     * Halts immediately upon failure without resetting previously filled inputs.
     * @param {Array<{name: string, fn: Function}>} steps
     * @returns {Object} { status: 'SUCCESS' | 'FAILED', failedStep?: number, name?: string, error?: string }
     */
    batch: function (steps) {
      if (!Array.isArray(steps)) {
        return { status: 'FAILED', error: 'Steps must be an array of {name, fn}' };
      }
      for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        try {
          if (typeof step.fn === 'function') {
            step.fn();
          } else if (typeof step.action === 'function') {
            step.action();
          } else {
            throw new Error(`Step #${i + 1} (${step.name}) has no runnable function.`);
          }
        } catch (err) {
          return {
            status: 'FAILED',
            failedStep: i + 1,
            stepName: step.name || `Step #${i + 1}`,
            error: err.message,
            preservedStateUrl: window.location.href
          };
        }
      }
      return { status: 'SUCCESS', totalSteps: steps.length };
    },

    /**
     * 2. Instant Form Audit
     * Finds all invalid fields in active forms (diagnosing disabled Save buttons).
     * Covers Angular Material, PrimeNG, Ant Design, Bootstrap, and HTML5 validation.
     * @returns {Array<Object>} List of invalid controls with metadata
     */
    audit: function () {
      const invalidNodes = Array.from(
        document.querySelectorAll(
          'form .ng-invalid, input.ng-invalid, mat-form-field.ng-invalid, mat-select.ng-invalid, textarea.ng-invalid, p-dropdown.ng-invalid, :invalid'
        )
      );
      return invalidNodes.map(el => ({
        tag: el.tagName.toLowerCase(),
        control: el.getAttribute('formcontrolname') || el.getAttribute('name') || el.id || 'unnamed',
        placeholder: el.getAttribute('placeholder') || '',
        classes: el.className,
        value: el.value || el.innerText.trim()
      }));
    },

    /**
     * 3. Self-Healing Locator Engine
     * When a selector returns 0 elements, scans DOM for matching text, label, or placeholder.
     * @param {string} brokenSelector
     * @param {string} [searchText]
     * @returns {Object} Suggested robust selector
     */
    heal: function (brokenSelector, searchText) {
      const query = (searchText || brokenSelector || '').replace(/['"\\\[\]]/g, '').trim().toLowerCase();
      const candidates = [];

      // Scan buttons
      document.querySelectorAll('button, a.p-button, span.p-button-text, .mat-mdc-button, [role="button"]').forEach(btn => {
        const txt = btn.innerText.trim().toLowerCase();
        if (query && txt.includes(query)) {
          candidates.push({
            type: 'button',
            text: btn.innerText.trim(),
            suggestedXPath: `//button[contains(normalize-space(.), '${btn.innerText.trim()}')]`,
            score: 0.95
          });
        }
      });

      // Scan inputs & form controls
      document.querySelectorAll('input, textarea, mat-select, p-dropdown, select').forEach(inp => {
        const fcn = inp.getAttribute('formcontrolname');
        const ph = inp.getAttribute('placeholder') || '';
        const name = inp.getAttribute('name');
        const testid = inp.getAttribute('data-testid');
        if (testid && testid.toLowerCase().includes(query)) {
          candidates.push({
            type: 'input',
            dataTestId: testid,
            suggestedCss: `[data-testid='${testid}']`,
            score: 0.99
          });
        } else if ((fcn || name) && ((fcn || name).toLowerCase().includes(query) || (query && ph.toLowerCase().includes(query)))) {
          const ctrl = fcn || name;
          candidates.push({
            type: 'input',
            formControlName: fcn,
            name: name,
            placeholder: ph,
            suggestedXPath: `//*[@formcontrolname='${ctrl}']`,
            suggestedCss: `[formcontrolname='${ctrl}']`,
            score: 0.98
          });
        }
      });

      return {
        originalSelector: brokenSelector,
        candidatesFound: candidates.length,
        bestMatch: candidates[0] || null
      };
    },

    /**
     * 4. Safe Click & Overlay Bypass
     * Dispatches click event directly, bypassing blocking overlays
     * (.cdk-overlay-backdrop, .p-component-overlay, .modal-backdrop).
     * @param {string | HTMLElement} target
     * @returns {boolean}
     */
    clickSafe: function (target) {
      const el = typeof target === 'string' ? document.querySelector(target) : target;
      if (!el) return false;

      // Temporarily neutralize blocking overlays if present
      document.querySelectorAll('.cdk-overlay-backdrop, .p-component-overlay, .modal-backdrop').forEach(overlay => {
        overlay.style.pointerEvents = 'none';
      });

      el.scrollIntoView({ behavior: 'auto', block: 'center' });
      el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
      el.click();
      return true;
    },

    /**
     * 5. Session State Exporter
     * Exports tokens and localStorage to bypass UI login (Zero-Second Auth).
     * @returns {Object}
     */
    exportSession: function () {
      const storage = {};
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        storage[key] = localStorage.getItem(key);
      }
      return {
        url: window.location.href,
        cookies: document.cookie,
        localStorage: storage
      };
    },

    /**
     * Restore session state
     * @param {Object} data
     */
    importSession: function (data) {
      if (data && data.localStorage) {
        for (const [k, v] of Object.entries(data.localStorage)) {
          localStorage.setItem(k, v);
        }
      }
      return { status: 'SESSION_IMPORTED' };
    },

    /**
     * 6. Zone.js & Microtask Stability Sync Engine
     * Checks if framework microtasks, promises, and animations are fully settled.
     * @returns {boolean}
     */
    isStable: function () {
      try {
        if (window.getAllAngularTestabilities) {
          const testabilities = window.getAllAngularTestabilities();
          if (testabilities && testabilities.length > 0) {
            return testabilities.every(t => t.isStable());
          }
        }
        const hasBlocker = document.querySelector(
          '.p-blockui, .p-progress-spinner, .mat-mdc-progress-bar, .spinner, .loading, .ng-animating'
        );
        return !hasBlocker;
      } catch (e) {
        return true;
      }
    },

    /**
     * Asynchronously wait for framework to become stable
     * @param {number} [timeoutMs=10000]
     * @returns {Promise<boolean>}
     */
    waitForStable: function (timeoutMs = 10000) {
      const self = this;
      const start = Date.now();
      return new Promise((resolve) => {
        const interval = setInterval(() => {
          if (self.isStable()) {
            clearInterval(interval);
            resolve(true);
          } else if (Date.now() - start > timeoutMs) {
            clearInterval(interval);
            resolve(false);
          }
        }, 100);
      });
    },

    /**
     * 7. CDP Network Drain & In-Flight Traffic Monitor (Network Idle 0)
     */
    getActiveRequests: function () {
      return activeNetworkRequests;
    },

    waitForNetworkIdle: function (idleTimeMs = 500, timeoutMs = 10000) {
      const start = Date.now();
      let idleStart = null;
      return new Promise((resolve) => {
        const interval = setInterval(() => {
          if (activeNetworkRequests === 0) {
            if (!idleStart) idleStart = Date.now();
            if (Date.now() - idleStart >= idleTimeMs) {
              clearInterval(interval);
              resolve(true);
            }
          } else {
            idleStart = null;
          }
          if (Date.now() - start > timeoutMs) {
            clearInterval(interval);
            resolve(false);
          }
        }, 50);
      });
    }
  };

  window.__qa = qa;
  window.__helper = qa;
  return qa;
})();
