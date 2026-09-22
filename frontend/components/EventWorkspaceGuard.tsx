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
  if (state === "anonymous") return <StateBlock title="Sign in required" message="Sign in to continue to this Ellenor Events workspace." />;
  if (state === "loading") return <StateBlock title="Loading" message="Preparing the latest event details." />;
  if (state === "empty") {
    return (
      <section className="grid twoColumns">
        <StateBlock title="Create your first event" message="Start an event to unlock the planning tools for that workspace." />
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
