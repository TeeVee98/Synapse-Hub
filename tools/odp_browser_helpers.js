/**
 * ODP Browser Runtime Helper (window.__odp) — CKAN Stack (jQuery + Bootstrap + Select2)
 *
 * Provides 8 AI Testing Capabilities directly inside the live browser DOM:
 * 1. Smart Action Batching (odp.batch) - Atomic execution with pause & state preservation.
 * 2. Instant Form Audit (odp.audit) - Detects CKAN/Bootstrap invalid fields in 1-shot.
 * 3. Self-Healing Locator Engine (odp.heal) - Suggests resilient selectors when locators break.
 * 4. Safe Click & Overlay Bypass (odp.clickSafe) - Clears Select2 drop-masks & modal backdrops before clicking.
 * 5. CKAN/jQuery Deterministic Sync Engine (odp.isStable / odp.waitForStable).
 * 6. CDP Network Drain & In-Flight Traffic Monitor (odp.getActiveRequests / odp.waitForNetworkIdle).
 * 7. Session State Exporter/Importer (odp.exportSession / odp.importSession).
 */

(function () {
  'use strict';

  if (window.__odp && window.__odp.__version === '1.0.0') {
    return window.__odp;
  }

  // Active in-flight network request tracker
  let activeNetworkRequests = 0;
  if (!window.__odp_net_hooked) {
    window.__odp_net_hooked = true;
    if (window.fetch) {
      const origFetch = window.fetch;
      window.fetch = function () {
        activeNetworkRequests++;
        return origFetch.apply(this, arguments).finally(() => {
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

  const odp = {
    __version: '1.0.0',

    /**
     * 1. Smart Action Batching
     * Runs a sequence of step functions atomically.
     * Halts immediately upon failure without resetting previously filled inputs.
     * @param {Array<{name: string, fn: Function}>} steps
     * @returns {Object} { status: 'SUCCESS' | 'FAILED', failedStep?: number, stepName?: string, error?: string }
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
     * 2. Instant Form Audit (CKAN / Bootstrap)
     * Finds all invalid fields in active forms (diagnosing no-op Save buttons).
     * Reads CKAN `.error-block` messages attached to the control group.
     * @returns {Array<Object>} List of invalid controls with metadata
     */
    audit: function () {
      const invalidNodes = Array.from(
        document.querySelectorAll('.has-error input, .has-error select, .has-error textarea, .control-group.error input, .control-group.error select, input:invalid, select:invalid, textarea:invalid')
      );
      return invalidNodes.map(el => {
        const group = el.closest('.control-group, .form-group');
        return {
          tag: el.tagName.toLowerCase(),
          control: el.getAttribute('name') || el.id || 'unnamed',
          placeholder: el.getAttribute('placeholder') || '',
          classes: el.className,
          errorBlock: group ? (group.querySelector('.error-block, .help-block.error, .invalid-feedback') || {}).innerText || '' : '',
          value: el.value || el.innerText.trim()
        };
      });
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

      // Scan buttons & links
      document.querySelectorAll('button, a.btn, a').forEach(btn => {
        const txt = btn.innerText.trim().toLowerCase();
        if (query && txt.includes(query)) {
          candidates.push({
            type: 'button',
            text: btn.innerText.trim(),
            suggestedXPath: `//button[contains(normalize-space(.), '${btn.innerText.trim()}')] | //a[contains(normalize-space(.), '${btn.innerText.trim()}')]`,
            score: 0.95
          });
        }
      });

      // Scan inputs & form controls (CKAN convention: id="field-*", name attributes)
      document.querySelectorAll('input, textarea, select').forEach(inp => {
        const id = inp.id || '';
        const name = inp.getAttribute('name') || '';
        const ph = inp.getAttribute('placeholder') || '';
        if ((id && id.toLowerCase().includes(query)) || (name && name.toLowerCase().includes(query)) || (query && ph.toLowerCase().includes(query))) {
          candidates.push({
            type: 'input',
            id: id,
            name: name,
            placeholder: ph,
            suggestedXPath: id ? `//*[@id='${id}']` : `//input[@name='${name}']`,
            suggestedCss: id ? `#${id}` : `[name='${name}']`,
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
     * Dispatches click event directly, bypassing blocking Select2 drop-masks and Bootstrap backdrops.
     * @param {string | HTMLElement} target
     * @returns {boolean}
     */
    clickSafe: function (target) {
      const el = typeof target === 'string' ? document.querySelector(target) : target;
      if (!el) return false;

      // Neutralize blocking overlays (Select2 mask, Bootstrap modal backdrop, fading overlays)
      document.querySelectorAll('.select2-drop-mask, .modal-backdrop, .select2-dropdown-open .select2-choice').forEach(overlay => {
        overlay.style.pointerEvents = 'none';
      });

      el.scrollIntoView({ behavior: 'auto', block: 'center' });
      el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
      // CKAN binds jQuery handlers — trigger through jQuery when available
      if (window.jQuery) {
        window.jQuery(el).trigger('click');
      }
      el.click();
      return true;
    },

    /**
     * 5. CKAN/jQuery Deterministic Sync Engine
     * Checks if the document is fully loaded, jQuery AJAX queue is drained,
     * and no visible loading indicator remains.
     * @returns {boolean}
     */
    isStable: function () {
      try {
        if (document.readyState !== 'complete') {
          return false;
        }
        if (window.jQuery && window.jQuery.active && window.jQuery.active > 0) {
          return false;
        }
        const hasBlocker = document.querySelector('.loading, .spinner, .select2-drop-mask, .loading-overlay');
        return !hasBlocker;
      } catch (e) {
        return true;
      }
    },

    /**
     * Asynchronously wait for CKAN page to become stable
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
     * 6. CDP Network Drain & In-Flight Traffic Monitor (Network Idle 0)
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
    },

    /**
     * 7. Session State Exporter
     * Exports CKAN session cookies and localStorage credentials to bypass UI login.
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
    }
  };

  window.__odp = odp;
  return odp;
})();
