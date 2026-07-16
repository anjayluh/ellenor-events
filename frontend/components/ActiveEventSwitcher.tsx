"use client";

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
  if (projects.length <= 1) return null;

  return (
    <section className="panel eventSwitcher" aria-label="Active event selector">
      <label className="formField">
        Active event workspace
        <select value={activeProjectId ?? ""} onChange={(event) => onChange(event.target.value)}>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.title} · {(project.role ?? "Member").replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <span className="helperText">Every budget, meeting, committee task, vendor, and invite below belongs to the selected event only.</span>
      </label>
    </section>
  );
}
