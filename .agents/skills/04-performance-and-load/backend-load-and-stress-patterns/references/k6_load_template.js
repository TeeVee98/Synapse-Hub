/**
 * Production-Ready k6 Load Testing Template
 * Features ramping arrival rate, kill-switch thresholds, user pooling, and per-VU session isolation.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

// 1. Parameterized Test Data: Load pre-seeded user pool to avoid single-token bottleneck
const userPool = new SharedArray('perf_users', function () {
  // In production: JSON.parse(open('./users.json')) or dynamic credential matrix
  return Array.from({ length: 200 }, (_, i) => ({
    username: `perf_user_${i + 1}@staging.enterprise.local`,
    password: `P@ssw0rd2026_${i + 1}`,
  }));
});

export const options = {
  discardResponseBodies: true,
  scenarios: {
    steady_load: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 200,
      stages: [
        { duration: '2m', target: 50 },  // Ramp-up
        { duration: '10m', target: 50 }, // Steady state (SLA measured here)
        { duration: '2m', target: 0 },   // Ramp-down
      ],
    },
  },
  thresholds: {
    // 1. Steady state SLA thresholds
    'http_req_failed{scenario:steady_load}': ['rate<0.01'],
    'http_req_duration{scenario:steady_load,expected_response:true}': ['p(95)<500', 'p(99)<1000'],
    'checks{scenario:steady_load}': ['rate>0.99'],
    'dropped_iterations{scenario:steady_load}': ['count==0'],
    // 2. Kill-switch: abort test if system fails catastrophically
    http_req_failed: [{ threshold: 'rate<0.10', abortOnFail: true, delayAbortEval: '30s' }],
  },
};

// 2. Virtual User journey (Authentic Per-VU Session Isolation)
export default function () {
  // Assign isolated user identity per virtual thread to avoid gateway concurrency lockups
  const user = userPool[__VU % userPool.length];

  // Per-VU authentic session acquisition
  const loginRes = http.post(`${__ENV.BASE_URL}/api/v1/auth/login`, JSON.stringify(user), {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: 'POST /api/v1/auth/login' },
  });

  check(loginRes, {
    'auth succeeded': (r) => r.status === 200 && r.json('token') !== undefined,
  });

  const authToken = loginRes.json('token');
  const params = {
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    },
    tags: { name: 'GET /api/v1/items' },
  };

  const res = http.get(`${__ENV.BASE_URL}/api/v1/items?page=1&limit=20`, params);
  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  // Realistic think time between actions (uniform 1s to 3s)
  sleep(Math.random() * 2 + 1);
}

// 3. Ephemeral teardown cleanup
export function teardown() {
  // Execute teardown API calls for created PERF_ entities
}
