import http from "k6/http";
import { check, sleep, group, fail } from "k6";

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8000";
const ADMIN_EMAIL = __ENV.ADMIN_EMAIL || "admin@example.com";
const ADMIN_PASSWORD = __ENV.ADMIN_PASSWORD || "admin";

export const options = {
    thresholds: {
        http_req_failed: ["rate<0.80"],
        "http_req_duration{name:health}": ["p(95)<5000"],
        "http_req_duration{name:graph_full}": ["p(95)<10000"],
        "http_req_duration{name:graph_stats}": ["p(95)<10000"],
        "checks": ["rate>0.90"],
    },
    scenarios: {
        smoke: {
            executor: "constant-vus",
            vus: 3,
            duration: "20s",
            gracefulStop: "5s",
        },
        ramp: {
            executor: "ramping-vus",
            startTime: "20s",
            startVUs: 0,
            stages: [
                { duration: "15s", target: 8 },
                { duration: "20s", target: 8 },
                { duration: "5s", target: 0 },
            ],
            gracefulRampDown: "5s",
        },
    },
};

// Runs ONCE before any VU starts. We acquire a token here and pass it
// through to every iteration, which is much closer to a real user session
// than re-logging-in each iteration (bcrypt thrashing, etc.).
export function setup() {
    const res = http.post(
        `${BASE}/api/v1/auth/login`,
        JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD }),
        { headers: { "Content-Type": "application/json" }, tags: { name: "login" } },
    );
    if (res.status !== 200 || !res.json("access_token")) {
        fail(`setup() login failed: status=${res.status} body=${res.body}`);
    }
    return { token: res.json("access_token") };
}

export default function (data) {
    const headers = {
        Authorization: `Bearer ${data.token}`,
        "Content-Type": "application/json",
    };

    group("anonymous probes", () => {
        const h = http.get(`${BASE}/health`, { tags: { name: "health" } });
        check(h, {
            "health: 200": (r) => r.status === 200,
            "health: status ok": (r) => r.json("status") === "ok",
        });

        const oa = http.get(`${BASE}/openapi.json`, { tags: { name: "openapi" } });
        check(oa, {
            "openapi: 200": (r) => r.status === 200,
            "openapi: 3.x": (r) => (r.json("openapi") || "").startsWith("3."),
        });
    });

    group("auth: bad credentials are rejected", () => {
        const r = http.post(
            `${BASE}/api/v1/auth/login`,
            JSON.stringify({ email: "admin@example.com", password: "definitely-wrong" }),
            {
                headers: { "Content-Type": "application/json" },
                tags: { name: "bad_login" },
            },
        );
        check(r, {
            "bad-login: 401": (res) => res.status === 401,
            "bad-login: detail present": (res) => !!res.json("detail"),
        });
    });

    group("auth: anonymous request to protected route is rejected", () => {
        const r = http.get(`${BASE}/api/v1/graph/full`, { tags: { name: "anon_graph" } });
        check(r, { "anon: 401": (res) => res.status === 401 });
    });

    group("authenticated: graph endpoints", () => {
        const stats = http.get(`${BASE}/api/v1/graph/stats`, {
            headers,
            tags: { name: "graph_stats" },
        });
        check(stats, { "stats: 2xx": (r) => r.status >= 200 && r.status < 300 });

        const full = http.get(`${BASE}/api/v1/graph/full?limit=100`, {
            headers,
            tags: { name: "graph_full" },
        });
        check(full, { "full: 2xx": (r) => r.status >= 200 && r.status < 300 });
    });

    sleep(1);
}
