import type { Project } from "./types";

const PROJECT_CACHE_KEY = "eecs_project_cache";

export function getCachedProjects(): Project[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(PROJECT_CACHE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as Project[];
  } catch {
    window.localStorage.removeItem(PROJECT_CACHE_KEY);
    return [];
  }
}

export function cacheProjects(projects: Project[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(PROJECT_CACHE_KEY, JSON.stringify(projects));
}

export function clearCachedProjects() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(PROJECT_CACHE_KEY);
}
