import { expireSession, getAccessToken } from "./session";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string, public sessionExpired = false) {
    super(message);
  }
}

function isPublicPath(path: string) {
  return path.startsWith("/auth/") || path === "/invites/accept" || /^\/invites\/[^/]+$/.test(path);
}

function resolveAccessToken(path: string, token?: string): string | null {
  if (isPublicPath(path)) return null;
  return token ?? getAccessToken();
}

async function parseResponse<T>(response: Response, hadAuth: boolean): Promise<T> {
  if (!response.ok) {
    let message = `API request failed: ${response.status}`;
    try {
      const payload = await response.json();
      message = typeof payload.detail === "string" ? payload.detail : message;
    } catch {
      // Keep default message when the response is not JSON.
    }
    if (response.status === 401 && hadAuth) {
      const sessionMessage = "Your session expired. Please sign in again.";
      expireSession(sessionMessage);
      throw new ApiError(response.status, sessionMessage, true);
    }
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string, token?: string): Promise<T> {
  const accessToken = resolveAccessToken(path, token);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    cache: "no-store"
  });
  return parseResponse<T>(response, Boolean(accessToken));
}

export async function apiPost<TResponse, TPayload>(path: string, payload: TPayload, token?: string): Promise<TResponse> {
  const accessToken = resolveAccessToken(path, token);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
    },
    body: JSON.stringify(payload)
  });
  return parseResponse<TResponse>(response, Boolean(accessToken));
}

export async function apiPatch<TResponse, TPayload>(path: string, payload: TPayload, token?: string): Promise<TResponse> {
  const accessToken = resolveAccessToken(path, token);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
    },
    body: JSON.stringify(payload)
  });
  return parseResponse<TResponse>(response, Boolean(accessToken));
}

export async function apiDelete<TResponse>(path: string, token?: string): Promise<TResponse> {
  const accessToken = resolveAccessToken(path, token);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
  });
  return parseResponse<TResponse>(response, Boolean(accessToken));
}
