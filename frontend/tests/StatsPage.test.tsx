import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, afterEach } from "vitest";
import { StatsPage } from "../src/pages/StatsPage";

function statsResponse(cache: "HIT" | "MISS") {
  return new Response(
    JSON.stringify({
      total: 5,
      by_category: { water: 3, roads: 2 },
      by_priority: { high: 1, normal: 4 },
      by_status: { open: 5 },
    }),
    { status: 200, headers: { "Content-Type": "application/json", "X-Cache": cache } },
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("StatsPage", () => {
  it("renders a HIT badge when X-Cache is HIT", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => statsResponse("HIT")),
    );
    render(<StatsPage />);
    expect(await screen.findByTestId("cache-badge")).toHaveTextContent("X-Cache: HIT");
  });

  it("renders a MISS badge when X-Cache is MISS", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => statsResponse("MISS")),
    );
    render(<StatsPage />);
    expect(await screen.findByTestId("cache-badge")).toHaveTextContent("X-Cache: MISS");
  });

  it("renders aggregate counts by category, priority and status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => statsResponse("HIT")),
    );
    render(<StatsPage />);
    expect(await screen.findByText(/Total complaints: 5/)).toBeInTheDocument();
    expect(screen.getByText("water")).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
    expect(screen.getByText("open")).toBeInTheDocument();
  });
});
