import type { AuthToken, AuthUser } from "./types";

const TOKEN_KEY = "eecs_access_token";
const USER_KEY = "eecs_user";
const AUTH_EVENT = "eecs-auth-change";

function emitAuthChange() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function saveSession(auth: AuthToken) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, auth.access_token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
  emitAuthChange();
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getSessionUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as AuthUser) : null;
}

export function clearSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
  emitAuthChange();
}

export function subscribeToAuthChanges(callback: () => void) {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener(AUTH_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(AUTH_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}
