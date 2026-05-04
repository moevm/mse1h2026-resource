import http from "k6/http";
import { check, sleep, group } from "k6";
import { Counter, Trend } from "k6/metrics";

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8000";
const ADMIN_EMAIL = __ENV.ADMIN_EMAIL || "admin@example.com";
const ADMIN_PASSWORD = __ENV.ADMIN_PASSWORD || "admin";

export const options = {
    thresholds: {
        http_req_failed: ["rate<0.02"],
        http_req_duration: ["p(95)<500"],
        "http_req_duration{name:health}": ["p(95)<150"],
        "http_req_duration{name:login}": ["p(95)<800"],
        "checks": ["rate>0.98"],
    },
    scenarios: {
        smoke: {
            executor: "constant-vus",
            vus: 5,
            duration: "30s",
            gracefulStop: "5s",
        },
        ramp: {
            executor: "ramping-vus",
            startTime: "30s",
            startVUs: 0,
            stages: [
                { duration: "20s", target: 20 },
                { duration: "30s", target: 20 },
                { duration: "10s", target: 0 },
            ],
            gracefulRampDown: "5s",
        },
    },
};

const loginCounter = new Counter("logins_total");
const tokenLifetime = new Trend("admin_token_age_ms", true);

function login() {
    const url = `${BASE}/api/v1/auth/login`;
    const payload = JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD });
    const params = {
        headers: { "Content-Type": "application/json" },
        tags: { name: "login" },
    };
    const res = http.post(url, payload, params);
    check(res, {
        "login: 200": (r) => r.status === 200,
        "login: returns access_token": (r) => !!r.json("access_token"),
        "login: returns refresh_token": (r) => !!r.json("refresh_token"),
    });
    loginCounter.add(1);
    return res.json("access_token");
}

export default function () {
    group("health", () => {
        const r = http.get(`${BASE}/health`, { tags: { name: "health" } });
        check(r, {
            "health: 200": (res) => res.status === 200,
            "health: status ok": (res) => res.json("status") === "ok",
        });
    });

    group("openapi", () => {
        const r = http.get(`${BASE}/openapi.json`, { tags: { name: "openapi" } });
        check(r, {
            "openapi: 200": (res) => res.status === 200,
            "openapi: 3.x": (res) => (res.json("openapi") || "").startsWith("3."),
        });
    });

    group("auth: invalid login is rejected", () => {
        const r = http.post(
            `${BASE}/api/v1/auth/login`,
            JSON.stringify({ email: "admin@example.com", password: "wrong-password" }),
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

    group("auth: protected route rejects anonymous", () => {
        const r = http.get(`${BASE}/api/v1/graph/full`, { tags: { name: "anon_graph" } });
        check(r, { "anon: 401": (res) => res.status === 401 });
    });

    const token = login();

    if (token) {
        const start = Date.now();
        group("graph endpoints with token", () => {
            const headers = {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
            };
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
        tokenLifetime.add(Date.now() - start);
    }

    sleep(0.5);
}
