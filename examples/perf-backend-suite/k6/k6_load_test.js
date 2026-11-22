// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

/**
 * k6_load_test.js — Archetype 2: Standard Peak Load Performance Test (ISTQB CT-PT & ISO/IEC 25010)
 * Uses open arrival-rate executor to model realistic public arrival traffic.
 * Enforces automated SLA thresholds and catastrophic kill-switch (abortOnFail).
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

// 1. Parameterized Test Data Pool
const userPool = new SharedArray('perf_users', function () {
  return Array.from({ length: 50 }, (_, i) => ({
    username: `perf_tester_${i + 1}@synapse.test`,
    password: `PerfSecure2026_${i + 1}!`,
  }));
});

export const options = {
  discardResponseBodies: false,
  scenarios: {
    steady_load: {
      executor: 'ramping-arrival-rate',
      startRate: 5,
      timeUnit: '1s',
      preAllocatedVUs: 20,
      maxVUs: 100,
      stages: [
        { duration: '30s', target: 20 },  // Ramp-up to baseline
        { duration: '2m', target: 20 },   // Steady-state evaluation window
        { duration: '30s', target: 0 },   // Ramp-down
      ],
    },
  },
  thresholds: {
    // Steady state SLA budgets
    'http_req_failed{scenario:steady_load}': ['rate<0.01'],
    'http_req_duration{scenario:steady_load,expected_response:true}': ['p(95)<500', 'p(99)<1000'],
    'checks{scenario:steady_load}': ['rate>0.99'],
    'dropped_iterations{scenario:steady_load}': ['count==0'],
    // Automatic Kill-Switch: Abort if catastrophic failures exceed 10%
    'http_req_failed': [{ threshold: 'rate<0.10', abortOnFail: true, delayAbortEval: '15s' }],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export default function () {
  const user = userPool[__VU % userPool.length];
  const rand = Math.random();

  // Traffic Shaping: Pareto Mix (70% Read, 20% Create, 10% Read Single)
  if (rand < 0.70) {
    // 70% Read All Books
    const res = http.get(`${BASE_URL}/api/v1/Books`, {
      headers: { 'Accept': 'application/json' },
      tags: { name: 'GET /api/v1/Books' },
    });
    check(res, {
      'get books status is 200': (r) => r.status === 200,
    });
  } else if (rand < 0.90) {
    // 20% Create Dynamic Book (Idempotent Synthetic Data)
    const uniqueTitle = `PERF_AUTO_BOOK_${Date.now()}_${__VU}_${__ITER}`;
    const payload = JSON.stringify({
      id: Math.floor(Math.random() * 900000) + 100000,
      title: uniqueTitle,
      description: 'Performance test synthetic book record',
      pageCount: 350,
      excerpt: 'Synthetic workload excerpt',
      publishDate: new Date().toISOString(),
    });

    const res = http.post(`${BASE_URL}/api/v1/Books`, payload, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      tags: { name: 'POST /api/v1/Books' },
    });
    check(res, {
      'create book status is 200 or 201': (r) => r.status === 200 || r.status === 201,
    });
  } else {
    // 10% Read Specific Item
    const targetId = Math.floor(Math.random() * 10) + 1;
    const res = http.get(`${BASE_URL}/api/v1/Books/${targetId}`, {
      headers: { 'Accept': 'application/json' },
      tags: { name: 'GET /api/v1/Books/:id' },
    });
    check(res, {
      'get single book status is 200': (r) => r.status === 200,
    });
  }

  // Realistic human think-time (1s to 2.5s)
  sleep(Math.random() * 1.5 + 1.0);
}

export function teardown() {
  // Teardown hook executes once after test concludes
}
