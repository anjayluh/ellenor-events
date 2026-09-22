import { expireSession, getAccessToken } from "./session";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

function defaultApiBaseUrl() {
  if (typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    return "http://127.0.0.1:8000";
  }
  return "";
}

function apiUrl(path: string) {
  const baseUrl = API_BASE_URL ?? defaultApiBaseUrl();
  return `${baseUrl}${path}`;
}

export class ApiError extends Error {
  constructor(public status: number, message: string, public sessionExpired = false) {
    super(message);
  }
}

function isPublicPath(path: string) {
  return path.startsWith("/auth/") || path === "/invites/accept" || /^\/invites\/[^/]+$/.test(path) || /^\/guest-invites\/[^/]+$/.test(path) || /^\/guest-invites\/[^/]+\/respond$/.test(path);
}

function resolveAccessToken(path: string, token?: string): string | null {
  if (isPublicPath(path)) return null;
  return token ?? getAccessToken();
}

async function parseResponse<T>(response: Response, hadAuth: boolean): Promise<T> {
  if (!response.ok) {
    let message = response.status === 401 ? "Please sign in again to continue." : `We could not complete that request (${response.status}).`;
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
  const response = await fetch(apiUrl(path), {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    cache: "no-store"
  });
  return parseResponse<T>(response, Boolean(accessToken));
}

export async function apiPost<TResponse, TPayload>(path: string, payload: TPayload, token?: string): Promise<TResponse> {
  const accessToken = resolveAccessToken(path, token);
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
    },
    body: JSON.stringify(payload)
  });
  return parseResponse<TResponse>(response, Boolean(accessToken));
}

export async function apiPut<TResponse, TPayload>(path: string, payload: TPayload, token?: string): Promise<TResponse> {
  const accessToken = resolveAccessToken(path, token);
  const response = await fetch(apiUrl(path), {
    method: "PUT",
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
  const response = await fetch(apiUrl(path), {
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
  const response = await fetch(apiUrl(path), {
    method: "DELETE",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
  });
  return parseResponse<TResponse>(response, Boolean(accessToken));
}
