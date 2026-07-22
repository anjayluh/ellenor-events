"use client";

import Link from "next/link";
import type { Project } from "../lib/types";

export function ActiveEventSwitcher({
  projects,
  activeProjectId,
  onChange
}: {
  projects: Project[];
  activeProjectId?: string;
  onChange: (projectId: string) => void;
}) {
  return (
    <section className="panel eventSwitcher" aria-label="Active event selector">
      <div className="eventSwitcherHeader">
        <label className="formField">
          Active event workspace
          <select value={activeProjectId ?? ""} disabled={projects.length <= 1} onChange={(event) => onChange(event.target.value)}>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.title} · {(project.role ?? "Member").replaceAll("_", " ")}
              </option>
            ))}
          </select>
          <span className="helperText">Every budget, meeting, committee task, vendor, and invite below belongs to the selected event only.</span>
        </label>
        {activeProjectId ? <Link className="ghostButton eventDetailsLink" href={`/events/${activeProjectId}`}>Back to event details</Link> : null}
      </div>
    </section>
  );
}
