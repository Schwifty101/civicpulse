import type { components } from "./schema";

export type Category = components["schemas"]["Category"];
export type Priority = components["schemas"]["Priority"];
export type Status = components["schemas"]["Status"];
export type ComplaintCreate = components["schemas"]["ComplaintCreate"];
export type ComplaintOut = components["schemas"]["ComplaintOut"];
export type ComplaintListOut = components["schemas"]["ComplaintListOut"];
export type StatsOut = components["schemas"]["StatsOut"];
export type ProvidersOut = components["schemas"]["ProvidersOut"];

export const CATEGORIES: Category[] = [
  "water",
  "electricity",
  "sanitation",
  "roads",
  "streetlights",
  "other",
];
export const PRIORITIES: Priority[] = ["high", "normal", "low"];
export const STATUSES: Status[] = ["open", "in_progress", "resolved", "rejected"];

/** The 400 field-error body — not accurately captured by FastAPI's auto-generated
 * OpenAPI doc (it only documents the default 422 shape), but this is what the
 * backend's custom validation-exception handler actually returns at runtime. */
export interface FieldErrorBody {
  detail: string;
  errors: { field: string; message: string }[];
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
    message: string,
  ) {
    super(message);
  }
}

export class RateLimitError extends ApiError {
  constructor(
    public retryAfterSeconds: number,
    body: unknown,
  ) {
    super(429, body, "rate limit exceeded");
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<{ data: T; headers: Headers }> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (res.status === 429) {
    const body = await res.json().catch(() => ({}));
    const retryAfter = Number(res.headers.get("Retry-After") ?? "0");
    throw new RateLimitError(retryAfter, body);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message =
      typeof body === "object" && body !== null && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `request failed with ${res.status}`;
    throw new ApiError(res.status, body, message);
  }

  const data = (await res.json()) as T;
  return { data, headers: res.headers };
}

export function createComplaint(payload: ComplaintCreate): Promise<{ data: ComplaintOut }> {
  return request<ComplaintOut>("/api/complaints", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getComplaint(id: string): Promise<{ data: ComplaintOut }> {
  return request<ComplaintOut>(`/api/complaints/${id}`);
}

export interface ListComplaintsParams {
  category?: Category;
  priority?: Priority;
  status?: Status;
  page?: number;
  page_size?: number;
}

export function listComplaints(
  params: ListComplaintsParams,
): Promise<{ data: ComplaintListOut }> {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") qs.set(key, String(value));
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<ComplaintListOut>(`/api/complaints${suffix}`);
}

export function updateStatus(id: string, status: Status): Promise<{ data: ComplaintOut }> {
  return request<ComplaintOut>(`/api/complaints/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function getStats(): Promise<{ data: StatsOut; cacheStatus: "HIT" | "MISS" | null }> {
  const { data, headers } = await request<StatsOut>("/api/stats");
  const cacheStatus = headers.get("X-Cache") as "HIT" | "MISS" | null;
  return { data, cacheStatus };
}

export function getProviders(): Promise<{ data: ProvidersOut }> {
  return request<ProvidersOut>("/api/meta/providers");
}
