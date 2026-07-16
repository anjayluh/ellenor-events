"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { EventDashboard } from "../../../components/EventDashboard";
import { PortalShell } from "../../../components/PortalShell";
import { StateBlock } from "../../../components/StateBlock";
import { apiGet } from "../../../lib/api";
import { getAccessToken } from "../../../lib/session";
import type { Project } from "../../../lib/types";

export default function EventPage() {
  const params = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [state, setState] = useState<"anonymous" | "loading" | "ready" | "error">("loading");

  useEffect(() => {
    const token = getAccessToken();
    if (!token) { setState("anonymous"); return; }
    void apiGet<Project>(`/projects/${params.projectId}`, token)
      .then((data) => { setProject(data); setState("ready"); })
      .catch(() => setState("error"));
  }, [params.projectId]);

  return (
    <PortalShell>
      {state === "anonymous" ? <StateBlock title="Login required" message="Sign in before viewing this event dashboard." /> : null}
      {state === "loading" ? <StateBlock title="Loading event" message="Fetching live project data from the API." /> : null}
      {state === "error" ? <StateBlock title="Event not found" message="The event could not be loaded for your account." /> : null}
      {state === "ready" && project ? <EventDashboard project={project} /> : null}
    </PortalShell>
  );
}
