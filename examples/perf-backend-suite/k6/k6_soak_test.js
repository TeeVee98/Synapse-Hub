// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

/**
 * k6_soak_test.js — Archetype 5: Endurance & Soak Performance Test (ISTQB CT-PT & ISO/IEC 25010)
 * Evaluates application reliability and stability under sustained nominal load over an extended duration.
 * Identifies memory leaks, unclosed database connection pools, thread depletion, and gradual latency drift.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

const SOAK_DURATION = __ENV.SOAK_DURATION || '15m';
const SOAK_VUS = parseInt(__ENV.SOAK_VUS || '30', 10);
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export const options = {
  stages: [
    { duration: '1m', target: SOAK_VUS },     // Ramp-up to sustained steady-state load
    { duration: SOAK_DURATION, target: SOAK_VUS }, // Sustained evaluation window (monitors memory & resource leaks)
    { duration: '1m', target: 0 },            // Graceful ramp-down
  ],
  thresholds: {
    // Stringent sustained SLA limits for long-running stability
    'http_req_failed': [
      'rate<0.005', // Cumulative error rate must stay below 0.5%
      { threshold: 'rate<0.05', abortOnFail: true, delayAbortEval: '30s' }, // Automatic Kill-Switch if failure exceeds 5%
    ],
    'http_req_duration': [
      'p(90)<400',  // 90% of requests must complete under 400ms
      'p(95)<600',  // 95% of requests must complete under 600ms
      'p(99)<1200', // 99% of requests must complete under 1200ms
    ],
    'checks': ['rate>0.995'], // Checks success rate >= 99.5%
  },
};

export default function () {
  const params = {
    headers: {
      'Accept': 'application/json',
      'User-Agent': 'Synapse-k6-SoakEngine/1.0',
    },
    tags: { name: 'GET /api/v1/Books (Soak)' },
  };

  // Sustained querying of catalog / collection endpoints
  const res = http.get(`${BASE_URL}/api/v1/Books?page=1&limit=20`, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response under 600ms': (r) => r.timings.duration < 600,
    'content type is json': (r) => r.headers['Content-Type'] && r.headers['Content-Type'].includes('json'),
  });

  // Realistic user pacing between requests (1s to 2s)
  sleep(Math.random() * 1.0 + 1.0);
}
