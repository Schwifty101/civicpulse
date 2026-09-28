// Load generator for the HPA scale-out demo (§3.3). Ramps virtual users up, holds, then
// ramps down — offered load over time, to compare against `kubectl get hpa -w` replica
// counts for the required replicas-vs-load chart.
//
// Usage: k6 run -e BASE_URL=http://civicpulse.local load/k6-script.js
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "1m", target: 10 },
    { duration: "3m", target: 80 }, // sustained load — this is what should trigger scale-out
    { duration: "2m", target: 80 },
    { duration: "1m", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

const SAMPLE_COMPLAINTS = [
  { text: "Burst water pipe flooding the street since this morning, urgent help needed.", location: "Street 12, G-9" },
  { text: "Streetlight has been broken for two weeks, area is very dark and unsafe at night.", location: "Sector I-8" },
  { text: "Garbage has not been collected in our block for over a week now, terrible smell.", location: "Liaquatabad" },
  { text: "Pothole on the main road is damaging cars daily, please repair urgently.", location: "Main Boulevard" },
  { text: "Transformer near the market is sparking, very dangerous for pedestrians nearby.", location: "Model Town" },
];

export default function () {
  const payload = SAMPLE_COMPLAINTS[Math.floor(Math.random() * SAMPLE_COMPLAINTS.length)];

  const createRes = http.post(`${BASE_URL}/api/complaints`, JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  });
  check(createRes, {
    "create is 201 or 429 (rate-limited is an acceptable, expected response)": (r) =>
      r.status === 201 || r.status === 429,
  });

  const listRes = http.get(`${BASE_URL}/api/complaints?page=1&page_size=20`);
  check(listRes, { "list is 200": (r) => r.status === 200 });

  http.get(`${BASE_URL}/api/stats`);

  sleep(Math.random() * 0.5);
}
