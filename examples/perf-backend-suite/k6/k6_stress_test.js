// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

/**
 * k6_stress_test.js — Archetype 3: Stress & Breakpoint Performance Test (ISTQB CT-PT)
 * Gradually ramps load to find the breaking point (degradation cliff) and verify
 * that the AUT degrades gracefully (returns HTTP 429 / 503 instead of crashing or leaking memory).
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },   // Warm-up
    { duration: '1m', target: 50 },    // Standard load
    { duration: '1m', target: 100 },   // Elevated stress
    { duration: '1m', target: 200 },   // Peak stress / saturation threshold
    { duration: '30s', target: 0 },    // Cool-down
  ],
  thresholds: {
    // Under stress, we expect graceful 429 Too Many Requests or 503 Service Unavailable, not 500 crashes
    'http_req_duration': ['p(90)<1500'],
    // Abort if failure rate exceeds 25% to protect backend infrastructure
    'http_req_failed': [{ threshold: 'rate<0.25', abortOnFail: true, delayAbortEval: '20s' }],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export default function () {
  const res = http.get(`${BASE_URL}/api/v1/Books`, {
    headers: { 'Accept': 'application/json' },
    tags: { name: 'GET /api/v1/Books (Stress)' },
  });

  check(res, {
    'response handled gracefully': (r) => r.status === 200 || r.status === 429 || r.status === 503,
  });

  // Short think-time to simulate rapid user activity under stress
  sleep(Math.random() * 0.8 + 0.2);
}
