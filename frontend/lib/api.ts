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

function userFacingMessage(status: number, detail: unknown): string {
  const raw = typeof detail === "string" ? detail : typeof detail === "object" && detail !== null && "message" in detail && typeof detail.message === "string" ? detail.message : "";
  const normalized = raw.toLowerCase();
  if (normalized.includes("invalid email or password") || normalized.includes("invalid credentials")) return "The email or password does not match. Please try again.";
  if (status === 409 || normalized.includes("already registered") || normalized.includes("already exists")) {
    return "An account already exists with this email. Choose Sign in instead. If you have not confirmed it yet, check your email for the confirmation link first.";
  }
  if (normalized.includes("supabase auth rejected account creation")) {
    return "We could not create your account yet. Check your details and try again. If you already used this email, choose Sign in or Reset password instead.";
  }
  if (normalized.includes("not confirmed") || normalized.includes("email address is not confirmed") || normalized.includes("confirm the email")) {
    return "Your account is not confirmed yet. Check the email address you signed up with for the confirmation link, then return here to sign in.";
  }
  if (status === 401 || normalized.includes("bearer token") || normalized.includes("invalid bearer")) return "Please sign in to continue.";
  if (status === 403 && (normalized.includes("admin") || normalized.includes("staff"))) return "This area is available to Ellenor Events team members only.";
  if (normalized.includes("not a member") || normalized.includes("not available to this account")) return "You do not have access to this event.";
  if (normalized.includes("insufficient") || normalized.includes("permission")) return "You do not have permission to do that.";
  if (status >= 500) return "Something went wrong on our side. Please try again in a moment.";
  return raw || `We could not complete that request (${status}).`;
}

function isPublicPath(path: string) {
  return path.startsWith("/auth/") || path.startsWith("/catalog/") || path === "/invites/accept" || /^\/invites\/[^/]+$/.test(path) || /^\/guest-invites\/[^/]+$/.test(path) || /^\/guest-invites\/[^/]+\/respond$/.test(path) || /^\/guest-rsvps\/[^/]+$/.test(path) || /^\/guest-rsvps\/[^/]+\/respond$/.test(path);
}

function resolveAccessToken(path: string, token?: string): string | null {
  if (isPublicPath(path)) return null;
  return token ?? getAccessToken();
}

async function parseResponse<T>(response: Response, hadAuth: boolean): Promise<T> {
  if (!response.ok) {
    let message = response.status === 401 ? "Please sign in to continue." : `We could not complete that request (${response.status}).`;
    let detail: unknown = "";
    try {
      const payload = await response.json();
      detail = payload.detail;
      message = userFacingMessage(response.status, detail);
    } catch {
      // Keep default message when the response is not JSON.
    }
    if (response.status === 401 && hadAuth) {
      const sessionMessage = "Your sign-in session has ended. Please sign in again.";
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

export async function apiUpload<TResponse>(path: string, formData: FormData, token?: string): Promise<TResponse> {
  const accessToken = resolveAccessToken(path, token);
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    body: formData
  });
  return parseResponse<TResponse>(response, Boolean(accessToken));
}

export async function apiDownload(path: string, token?: string): Promise<{ blob: Blob; filename: string | null }> {
  const accessToken = resolveAccessToken(path, token);
  const response = await fetch(apiUrl(path), {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    cache: "no-store"
  });
  if (!response.ok) {
    await parseResponse<never>(response, Boolean(accessToken));
  }
  const disposition = response.headers.get("Content-Disposition");
  const filename = disposition?.match(/filename="?([^";]+)"?/i)?.[1] ?? null;
  return { blob: await response.blob(), filename };
}
