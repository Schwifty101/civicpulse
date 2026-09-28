import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi, afterEach } from "vitest";
import { DashboardPage } from "../src/pages/DashboardPage";

const SAMPLE_COMPLAINT = {
  id: "22222222-2222-2222-2222-222222222222",
  text: "Garbage has not been collected in a week",
  location: "Liaquatabad",
  reporter_contact: null,
  category: "sanitation",
  priority: "normal",
  status: "open",
  ai_summary: "Garbage not collected",
  triaged_by: "rules",
  triage_latency_ms: 4,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("DashboardPage", () => {
  it("renders paginated items returned by the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({ items: [SAMPLE_COMPLAINT], total: 1, page: 1, page_size: 10 }),
      ),
    );

    render(<DashboardPage />);
    expect(await screen.findByText("Liaquatabad")).toBeInTheDocument();
    expect(screen.getByText(/1 total/)).toBeInTheDocument();
  });

  it("re-fetches with the selected category/priority/status as query params", async () => {
    const fetchMock = vi.fn(async (_url: string) =>
      jsonResponse({ items: [], total: 0, page: 1, page_size: 10 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<DashboardPage />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    fireEvent.change(screen.getByLabelText("Category"), { target: { value: "water" } });
    fireEvent.change(screen.getByLabelText("Priority"), { target: { value: "high" } });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "open" } });

    await waitFor(() => {
      const lastCallUrl = fetchMock.mock.calls.at(-1)?.[0] as string;
      expect(lastCallUrl).toContain("category=water");
      expect(lastCallUrl).toContain("priority=high");
      expect(lastCallUrl).toContain("status=open");
    });
  });

  it("surfaces the server's 409 message verbatim when a status change is rejected", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (init?.method === "PATCH") {
        return jsonResponse(
          { detail: "cannot transition from 'open' to 'resolved'" },
          409,
        );
      }
      if (url.includes("/api/complaints")) {
        return jsonResponse({ items: [SAMPLE_COMPLAINT], total: 1, page: 1, page_size: 10 });
      }
      return jsonResponse({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<DashboardPage />);
    const row = await screen.findByTestId("complaint-row");
    fireEvent.click(within(row).getByRole("button", { name: "→ resolved" }));

    expect(await within(row).findByRole("alert")).toHaveTextContent(
      "cannot transition from 'open' to 'resolved'",
    );
  });
});
