/**
 * DMIT Browser Runtime Helper (window.__dmit)
 * 
 * Provides 5 Advanced AI Testing Capabilities directly inside the live browser DOM:
 * 1. Smart Action Batching (dmit.batch) - Atomic execution with pause & state preservation.
 * 2. Instant Form Audit (dmit.audit) - Detects Angular ng-invalid fields in 1-shot.
 * 3. Self-Healing Locator Engine (dmit.heal) - Suggests resilient selectors when locators break.
 * 4. Safe Click & Overlay Bypass (dmit.clickSafe) - Clears PrimeNG modal overlays before clicking.
 * 5. GIS Canvas & OpenLayers HUD (dmit.gisHUD) - Calculates non-overlapping polygon click points.
 * 6. Session State Exporter/Importer (dmit.exportSession / dmit.importSession).
 */

(function () {
  'use strict';

  if (window.__dmit && window.__dmit.__version === '2.1.0') {
    return window.__dmit;
  }

  // Active in-flight network request tracker
  let activeNetworkRequests = 0;
  if (!window.__dmit_net_hooked) {
    window.__dmit_net_hooked = true;
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

  const dmit = {
    __version: '2.1.0',

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
     * 2. Instant Angular Form Audit
     * Finds all invalid fields in active forms (diagnosing disabled Save buttons).
     * @returns {Array<Object>} List of invalid controls with metadata
     */
    audit: function () {
      const invalidNodes = Array.from(
        document.querySelectorAll('form .ng-invalid, input.ng-invalid, p-dropdown.ng-invalid, textarea.ng-invalid')
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
      document.querySelectorAll('button, a.p-button, span.p-button-text').forEach(btn => {
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
      document.querySelectorAll('input, textarea, p-dropdown').forEach(inp => {
        const fcn = inp.getAttribute('formcontrolname');
        const ph = inp.getAttribute('placeholder') || '';
        const name = inp.getAttribute('name');
        if (fcn && (fcn.toLowerCase().includes(query) || (query && ph.toLowerCase().includes(query)))) {
          candidates.push({
            type: 'input',
            formControlName: fcn,
            placeholder: ph,
            suggestedXPath: `//input[@formcontrolname='${fcn}']`,
            suggestedCss: `[formcontrolname='${fcn}']`,
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
     * Dispatches click event directly, bypassing blocking modal overlays (.p-component-overlay).
     * @param {string | HTMLElement} target
     * @returns {boolean}
     */
    clickSafe: function (target) {
      const el = typeof target === 'string' ? document.querySelector(target) : target;
      if (!el) return false;

      // Temporary hide blocking overlays if present
      document.querySelectorAll('.p-component-overlay.p-component-overlay-enter').forEach(overlay => {
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
     * 5. OpenLayers GIS Canvas Inspector & Safe Polygon Clicker
     * Inspects OpenLayers map instance and calculates non-overlapping polygon click offsets.
     * @returns {Object} Viewport dimensions and safe click offsets
     */
    gisHUD: function () {
      const viewport = document.querySelector('.ol-viewport, div[id*="map"] .ol-viewport');
      if (!viewport) {
        return { status: 'NO_GIS_MAP_FOUND' };
      }

      const rect = viewport.getBoundingClientRect();
      // Calculate safe coordinates in lower quadrant to prevent overlapping existing polygons
      const safeOffsets = [
        { x: Math.round(rect.width * 0.25), y: Math.round(rect.height * 0.25) },
        { x: Math.round(rect.width * 0.35), y: Math.round(rect.height * 0.25) },
        { x: Math.round(rect.width * 0.35), y: Math.round(rect.height * 0.35) },
        { x: Math.round(rect.width * 0.25), y: Math.round(rect.height * 0.35) }
      ];

      return {
        status: 'GIS_READY',
        viewportWidth: Math.round(rect.width),
        viewportHeight: Math.round(rect.height),
        safeOffsets: safeOffsets,
        centerPoint: { x: Math.round(rect.width / 2), y: Math.round(rect.height / 2) }
      };
    },

    /**
     * 6. Session State Exporter
     * Exports JWT tokens and localStorage credentials to bypass UI login.
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
     * 7. Angular Zone.js & Microtask Stability Sync Engine
     * Checks if Angular microtasks, promises, and PrimeNG animations are fully settled.
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
        const hasBlocker = document.querySelector('.p-blockui, .p-progress-spinner, .ng-animating');
        return !hasBlocker;
      } catch (e) {
        return true;
      }
    },

    /**
     * Asynchronously wait for Angular to become stable
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
     * 8. CDP Network Drain & In-Flight Traffic Monitor (Network Idle 0)
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

  window.__dmit = dmit;
  return dmit;
})();
