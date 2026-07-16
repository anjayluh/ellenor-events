"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import { getAccessToken, subscribeToAuthChanges } from "../lib/session";
import type { Project } from "../lib/types";
import { EventCard } from "./EventCard";
import { StateBlock } from "./StateBlock";

export function MyEventsPanel() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [status, setStatus] = useState<"anonymous" | "loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");

  async function loadProjects() {
    const token = getAccessToken();
    if (!token) {
      setProjects([]);
      setStatus("anonymous");
      return;
    }

    setStatus("loading");
    try {
      setProjects(await apiGet<Project[]>("/projects", token));
      setStatus("ready");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load projects.");
      setStatus("error");
    }
  }

  useEffect(() => {
    void loadProjects();
    return subscribeToAuthChanges(() => void loadProjects());
  }, []);

  if (status === "anonymous") {
    return (
      <StateBlock
        title="Sign in to view your events"
        message="Personal events, budgets, vendors, meetings, and staff tools stay hidden until you authenticate."
      />
    );
  }

  if (status === "loading") {
    return <StateBlock title="Loading your events" message="Fetching live project data from the API." />;
  }

  if (status === "error") {
    return <StateBlock title="Could not load events" message={message} />;
  }

  if (projects.length === 0) {
    return <StateBlock title="No events yet" message="Once you are added to an event, it will appear here." />;
  }

  return (
    <section className="panel">
      <h2>Your Events</h2>
      <div className="stack">
        {projects.map((event) => (
          <EventCard
            key={event.id}
            id={event.id}
            title={event.title}
            role={event.role ?? "Member"}
            type={event.type}
            date={event.event_date ?? "TBC"}
          />
        ))}
      </div>
    </section>
  );
}
