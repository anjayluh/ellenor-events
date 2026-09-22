"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet } from "./api";
import { getActiveProjectId, setActiveProjectId, subscribeToActiveProjectChanges } from "./active-project";
import { cacheProjects, getCachedProjects } from "./project-cache";
import { getAccessToken, subscribeToAuthChanges } from "./session";
import type { Project } from "./types";

type ActiveProjectState = "anonymous" | "loading" | "ready" | "empty" | "selection_required" | "error";

function getQueryProjectId() {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get("project");
}

export function useActiveProject() {
  const [projects, setProjects] = useState<Project[]>(() => getCachedProjects());
  const [project, setProject] = useState<Project | null>(() => {
    const cachedProjects = getCachedProjects();
    const preferredProjectId = getQueryProjectId() || getActiveProjectId();
    return preferredProjectId ? cachedProjects.find((item) => item.id === preferredProjectId) ?? null : null;
  });
  const [state, setState] = useState<ActiveProjectState>(() => {
    const cachedProjects = getCachedProjects();
    if (cachedProjects.length === 0) return "loading";
    const preferredProjectId = getQueryProjectId() || getActiveProjectId();
    if (!preferredProjectId && cachedProjects.length === 1) return "ready";
    return preferredProjectId && cachedProjects.some((item) => item.id === preferredProjectId) ? "ready" : "selection_required";
  });
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setProjects([]);
      setProject(null);
      setState("anonymous");
      return;
    }

    setState("loading");
    try {
      const nextProjects = await apiGet<Project[]>("/projects", token);
      setProjects(nextProjects);
      cacheProjects(nextProjects);

      const storedProjectId = getActiveProjectId();
      const preferredProjectId = getQueryProjectId() || storedProjectId;
      const selectedProject = preferredProjectId ? nextProjects.find((item) => item.id === preferredProjectId) ?? null : null;

      if (selectedProject) {
        setActiveProjectId(selectedProject.id);
        setProject(selectedProject);
        setMessage("");
        setState("ready");
      } else if (nextProjects.length === 1 && !preferredProjectId) {
        setActiveProjectId(nextProjects[0].id);
        setProject(nextProjects[0]);
        setMessage("");
        setState("ready");
      } else if (nextProjects.length > 0) {
        setProject(null);
        setMessage(preferredProjectId ? "That event is not available to this account. Choose an event you belong to." : "Choose the event workspace for this action.");
        setState("selection_required");
      } else {
        setProject(null);
        setMessage("");
        setState("empty");
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setProjects([]);
        setProject(null);
        setMessage(error.message);
        setState("anonymous");
        return;
      }
      setMessage(error instanceof Error ? error.message : "Could not load your event access.");
      setState("error");
    }
  }, []);

  function selectProject(projectId: string) {
    const selectedProject = projects.find((item) => item.id === projectId) ?? null;
    if (!selectedProject) return;
    setActiveProjectId(projectId);
    setProject(selectedProject);
    setMessage("");
    setState("ready");
  }

  useEffect(() => {
    void load();
    const unsubscribeAuth = subscribeToAuthChanges(() => void load());
    const unsubscribeProject = subscribeToActiveProjectChanges(() => void load());
    return () => {
      unsubscribeAuth();
      unsubscribeProject();
    };
  }, [load]);

  return { projects, project, state, message, selectProject, reload: load };
}
