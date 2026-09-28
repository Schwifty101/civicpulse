import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, afterEach } from "vitest";
import { SubmitPage } from "../src/pages/SubmitPage";

function fillForm(text: string, location: string) {
  fireEvent.change(screen.getByLabelText("Complaint"), { target: { value: text } });
  fireEvent.change(screen.getByLabelText("Location"), { target: { value: location } });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SubmitPage", () => {
  it("blocks submission client-side when text is too short and never calls fetch", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<SubmitPage />);

    fillForm("too short", "Street 12, G-9");
    fireEvent.click(screen.getByRole("button", { name: /submit complaint/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/between 10 and 2000/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows an honest loading state while the request is pending", async () => {
    let resolveFetch: (value: Response) => void = () => {};
    const pending = new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(() => pending),
    );

    render(<SubmitPage />);
    fillForm(
      "Burst water main flooding Street 12 since fajr, water entering ground floors.",
      "Street 12, G-9",
    );
    fireEvent.click(screen.getByRole("button", { name: /submit complaint/i }));

    expect(await screen.findByRole("button", { name: /triaging/i })).toBeDisabled();

    resolveFetch(
      new Response(
        JSON.stringify({
          id: "11111111-1111-1111-1111-111111111111",
          text: "x",
          location: "y",
          reporter_contact: null,
          category: "water",
          priority: "high",
          status: "open",
          ai_summary: "Water issue",
          triaged_by: "rules",
          triage_latency_ms: 3,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    await waitFor(() => expect(screen.getByTestId("result-card")).toBeInTheDocument());
  });

  it("renders category, priority, summary and provider on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            id: "11111111-1111-1111-1111-111111111111",
            text: "x",
            location: "y",
            reporter_contact: null,
            category: "streetlights",
            priority: "low",
            status: "open",
            ai_summary: "Streetlight is broken",
            triaged_by: "rules",
            triage_latency_ms: 5,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    render(<SubmitPage />);
    fillForm("Streetlight has been broken for over a week now near the park.", "Sector I-8");
    fireEvent.click(screen.getByRole("button", { name: /submit complaint/i }));

    const card = await screen.findByTestId("result-card");
    expect(card).toHaveTextContent("streetlights");
    expect(card).toHaveTextContent("low");
    expect(card).toHaveTextContent("Streetlight is broken");
    expect(card).toHaveTextContent("rules");
  });

  it("shows the server's Retry-After wait on a 429 response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "rate limit exceeded" }), {
          status: 429,
          headers: { "Content-Type": "application/json", "Retry-After": "42" },
        }),
      ),
    );

    render(<SubmitPage />);
    fillForm("Burst water main flooding Street 12 since fajr, water entering floors.", "Street 12");
    fireEvent.click(screen.getByRole("button", { name: /submit complaint/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/42 seconds/i);
  });
});
