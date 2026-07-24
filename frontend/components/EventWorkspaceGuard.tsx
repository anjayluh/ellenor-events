"use client";

import type { Project } from "../lib/types";
import { ActiveEventSwitcher } from "./ActiveEventSwitcher";
import { ProjectOnboardingForm } from "./ProjectOnboardingForm";
import { StateBlock } from "./StateBlock";

export function EventWorkspaceGuard({
  state,
  message,
  projects,
  onSelect,
  onCreated
}: {
  state: string;
  message?: string;
  projects: Project[];
  onSelect: (projectId: string) => void;
  onCreated: () => void;
}) {
  if (state === "anonymous") return <StateBlock title="Login required" message="Sign in before viewing private event data." />;
  if (state === "loading") return <StateBlock title="Loading" message="Fetching live event data." />;
  if (state === "empty") {
    return (
      <section className="grid twoColumns">
        <StateBlock title="Create your first event" message="Start an event before managing budget, committee, vendors, or guest RSVPs." />
        <ProjectOnboardingForm onCreated={onCreated} />
      </section>
    );
  }
  if (state === "selection_required") {
    return (
      <section className="panel actionPanel eventSelectionPanel">
        <p className="eyebrow">Choose Event</p>
        <h2>This page needs an event workspace.</h2>
        <p>{message || "Pick the exact event you want to manage."}</p>
        <div className="stack">
          {projects.map((project) => (
            <button className="ghostButton eventChoiceButton" data-icon="→" key={project.id} type="button" onClick={() => onSelect(project.id)}>
              <span>{project.title}</span>
              <small>{(project.role ?? "Member").replaceAll("_", " ")}</small>
            </button>
          ))}
        </div>
      </section>
    );
  }
  if (state === "error") return <StateBlock title="Could not load data" message={message || "Please try again."} />;
  return null;
}

export function EventScopedHeader({ projects, project, onSelect }: { projects: Project[]; project?: Project | null; onSelect: (projectId: string) => void }) {
  return <ActiveEventSwitcher projects={projects} activeProjectId={project?.id} onChange={onSelect} />;
}
