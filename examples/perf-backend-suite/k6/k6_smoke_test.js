// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

/**
 * k6_smoke_test.js — Archetype 1: Smoke / Sanity Performance Test (ISTQB CT-PT)
 * Fast verification that backend endpoints are reachable and responsive under minimal load.
 * SLA: Error rate = 0.0%, P95 < 300ms.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 5,
  duration: '1m',
  thresholds: {
    'http_req_failed': ['rate==0.0'],
    'http_req_duration': ['p(95)<300', 'p(99)<500'],
    'checks': ['rate==1.0'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://book.anhtester.com';

export default function () {
  const res = http.get(`${BASE_URL}/api/v1/Books`, {
    headers: { 'Accept': 'application/json' },
    tags: { name: 'GET /api/v1/Books (Smoke)' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'body has content': (r) => r.body && r.body.length > 0,
  });

  sleep(1);
}
