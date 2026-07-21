const ACTIVE_PROJECT_KEY = "eecs_active_project_id";
const ACTIVE_PROJECT_EVENT = "eecs-active-project-change";

export function getActiveProjectId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACTIVE_PROJECT_KEY);
}

export function setActiveProjectId(projectId: string) {
  if (typeof window === "undefined") return;
  if (window.localStorage.getItem(ACTIVE_PROJECT_KEY) === projectId) return;
  window.localStorage.setItem(ACTIVE_PROJECT_KEY, projectId);
  window.dispatchEvent(new Event(ACTIVE_PROJECT_EVENT));
}

export function clearActiveProjectId() {
  if (typeof window === "undefined") return;
  if (!window.localStorage.getItem(ACTIVE_PROJECT_KEY)) return;
  window.localStorage.removeItem(ACTIVE_PROJECT_KEY);
  window.dispatchEvent(new Event(ACTIVE_PROJECT_EVENT));
}

export function subscribeToActiveProjectChanges(callback: () => void) {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener(ACTIVE_PROJECT_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(ACTIVE_PROJECT_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}
