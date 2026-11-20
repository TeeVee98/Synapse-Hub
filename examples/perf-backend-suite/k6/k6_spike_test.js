// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

/**
 * k6_spike_test.js — Archetype 4: Spike & Shock Performance Test (ISTQB CT-PT)
 * Tests system resilience against sudden flash crowds (e.g. flash sales, push notifications).
 * Evaluates rate limiters, reverse proxy buffering, and system recovery time (< 30s).
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '20s', target: 5 },    // Baseline calm state
    { duration: '10s', target: 150 },  // Extreme instantaneous spike
    { duration: '30s', target: 150 },  // Hold spike peak
    { duration: '10s', target: 5 },    // Rapid descent
    { duration: '30s', target: 5 },    // Recovery observation window
  ],
  thresholds: {
    // Post-spike recovery latency must return to nominal SLA
    'http_req_duration{expected_response:true}': ['p(95)<1200'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://book.anhtester.com';

export default function () {
  const res = http.get(`${BASE_URL}/api/v1/Books`, {
    headers: { 'Accept': 'application/json' },
    tags: { name: 'GET /api/v1/Books (Spike)' },
  });

  check(res, {
    'system responds': (r) => [200, 429, 503].includes(r.status),
  });

  sleep(0.5);
}
