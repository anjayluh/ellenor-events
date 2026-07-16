"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiGet } from "./api";
import { getActiveProjectId, setActiveProjectId, subscribeToActiveProjectChanges } from "./active-project";
import { getAccessToken, subscribeToAuthChanges } from "./session";
import type { Project } from "./types";

type ActiveProjectState = "anonymous" | "loading" | "ready" | "empty" | "error";

export function useActiveProject() {
  const searchParams = useSearchParams();
  const queryProjectId = searchParams.get("project");
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [state, setState] = useState<ActiveProjectState>("loading");
  const [message, setMessage] = useState("");

  async function load() {
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

      const storedProjectId = getActiveProjectId();
      const preferredProjectId = queryProjectId || storedProjectId;
      const selectedProject = nextProjects.find((item) => item.id === preferredProjectId) ?? nextProjects[0] ?? null;

      if (selectedProject) {
        setActiveProjectId(selectedProject.id);
        setProject(selectedProject);
        setState("ready");
      } else {
        setProject(null);
        setState("empty");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load your project membership.");
      setState("error");
    }
  }

  function selectProject(projectId: string) {
    const selectedProject = projects.find((item) => item.id === projectId) ?? null;
    if (!selectedProject) return;
    setActiveProjectId(projectId);
    setProject(selectedProject);
  }

  useEffect(() => {
    void load();
    const unsubscribeAuth = subscribeToAuthChanges(() => void load());
    const unsubscribeProject = subscribeToActiveProjectChanges(() => void load());
    return () => {
      unsubscribeAuth();
      unsubscribeProject();
    };
  }, [queryProjectId]);

  return { projects, project, state, message, selectProject, reload: load };
}
