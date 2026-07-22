import type { AuthToken, AuthUser } from "./types";
import { clearActiveProjectId } from "./active-project";

const TOKEN_KEY = "eecs_access_token";
const USER_KEY = "eecs_user";
const AUTH_EVENT = "eecs-auth-change";
const SESSION_NOTICE_KEY = "eecs_session_notice";

type SessionClearReason = "manual" | "expired";
type AuthChangeDetail = { reason?: SessionClearReason; message?: string };

function emitAuthChange(detail: AuthChangeDetail = {}) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<AuthChangeDetail>(AUTH_EVENT, { detail }));
}

export function saveSession(auth: AuthToken) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, auth.access_token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
  window.sessionStorage.removeItem(SESSION_NOTICE_KEY);
  emitAuthChange();
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getSessionUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  if (!getAccessToken()) {
    window.localStorage.removeItem(USER_KEY);
    clearActiveProjectId();
    return null;
  }
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    expireSession("Your saved session could not be read. Please sign in again.");
    return null;
  }
}

export function clearSession(reason: SessionClearReason = "manual", message?: string) {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
  if (reason === "expired" && message) {
    window.sessionStorage.setItem(SESSION_NOTICE_KEY, message);
  } else if (reason === "manual") {
    window.sessionStorage.removeItem(SESSION_NOTICE_KEY);
  }
  clearActiveProjectId();
  emitAuthChange({ reason, message });
}

export function expireSession(message = "Your session expired. Please sign in again.") {
  clearSession("expired", message);
}

export function consumeSessionNotice(): string {
  if (typeof window === "undefined") return "";
  const notice = window.sessionStorage.getItem(SESSION_NOTICE_KEY) ?? "";
  window.sessionStorage.removeItem(SESSION_NOTICE_KEY);
  return notice;
}

export function subscribeToAuthChanges(callback: (detail?: AuthChangeDetail) => void) {
  if (typeof window === "undefined") return () => undefined;
  const onAuthChange = (event: Event) => callback((event as CustomEvent<AuthChangeDetail>).detail);
  const onStorage = () => callback();
  window.addEventListener(AUTH_EVENT, onAuthChange);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(AUTH_EVENT, onAuthChange);
    window.removeEventListener("storage", onStorage);
  };
}
