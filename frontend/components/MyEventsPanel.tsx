"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet } from "../lib/api";
import { setActiveProjectId } from "../lib/active-project";
import { cacheProjects, getCachedProjects } from "../lib/project-cache";
import { getAccessToken, subscribeToAuthChanges } from "../lib/session";
import type { Project } from "../lib/types";
import { EventCard } from "./EventCard";
import { ProjectOnboardingForm } from "./ProjectOnboardingForm";
import { StateBlock } from "./StateBlock";

export function MyEventsPanel() {
  const [projects, setProjects] = useState<Project[]>(() => getCachedProjects());
  const [status, setStatus] = useState<"anonymous" | "loading" | "ready" | "error">(() => getCachedProjects().length > 0 ? "ready" : "loading");
  const [message, setMessage] = useState("");

  const loadProjects = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setProjects([]);
      setStatus("anonymous");
      return;
    }

    if (projects.length === 0) setStatus("loading");
    try {
      const nextProjects = await apiGet<Project[]>("/projects", token);
      setProjects(nextProjects);
      cacheProjects(nextProjects);
      setStatus("ready");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setProjects([]);
        setMessage(error.message);
        setStatus("anonymous");
        return;
      }
      setMessage(error instanceof Error ? error.message : "Could not load your events.");
      setStatus("error");
    }
  }, [projects.length]);

  useEffect(() => {
    void loadProjects();
    return subscribeToAuthChanges(() => void loadProjects());
  }, [loadProjects]);

  if (status === "anonymous") {
    return (
      <StateBlock
        title="Sign in to view your events"
        message="Sign in to see the events connected to your Ellenor Events account."
      />
    );
  }

  if (status === "loading") {
    return <StateBlock title="Loading your events" message="Preparing your latest event workspaces." />;
  }

  if (status === "error") {
    return <StateBlock title="Could not load events" message={message} />;
  }

  if (projects.length === 0) {
    return (
      <section className="grid twoColumns">
        <StateBlock title="No events yet" message="Create your first event workspace, or accept an invitation from an owner or committee chair." />
        <ProjectOnboardingForm onCreated={() => void loadProjects()} />
      </section>
    );
  }

  return (
    <section className="panel actionPanel">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">My Workspaces</p>
          <h2>Your Events</h2>
        </div>
        <span className="badge">{projects.length} active</span>
      </div>
      <div className="stack">
        {projects.map((event) => (
          <EventCard
            key={event.id}
            id={event.id}
            title={event.title}
            role={event.role ?? "Member"}
            type={event.type}
            date={event.event_date ?? "TBC"}
            onOpen={() => setActiveProjectId(event.id)}
          />
        ))}
      </div>
      <details className="inlineDisclosure">
        <summary>Start another event</summary>
        <ProjectOnboardingForm onCreated={() => void loadProjects()} />
      </details>
    </section>
  );
}
