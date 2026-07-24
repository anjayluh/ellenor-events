"use client";

import { FormEvent, useState } from "react";
import { BudgetPreview } from "./BudgetPreview";
import { RoleAwareNav } from "./RoleAwareNav";
import { apiPatch, apiPost } from "../lib/api";
import type { Project, ProjectRole } from "../lib/types";

const EVENT_ADMIN_ROLES: ProjectRole[] = ["OWNER", "PARTNER", "COMMITTEE_CHAIR"];
const EVENT_ARCHIVE_ROLES: ProjectRole[] = ["OWNER", "PARTNER"];

export function EventDashboard({ project }: { project: Project }) {
  const [currentProject, setCurrentProject] = useState(project);
  const [title, setTitle] = useState(project.title);
  const [eventDate, setEventDate] = useState(project.event_date ?? "");
  const [message, setMessage] = useState("Event owners and leads can keep the core event details up to date.");
  const [processing, setProcessing] = useState<string | null>(null);
  const role = currentProject.role ?? "FAMILY_VIEWER";
  const visibility = currentProject.budget_visibility_mode ?? "NO_ACCESS";
  const canEditEvent = EVENT_ADMIN_ROLES.includes(role);
  const canArchiveEvent = EVENT_ARCHIVE_ROLES.includes(role);
  const titleError = title && title.trim().length < 4 ? "Event title must be at least 4 characters." : "";
  const eventChanged = title.trim() !== currentProject.title || (eventDate || null) !== currentProject.event_date;
  const canSave = canEditEvent && eventChanged && title.trim().length >= 4 && !titleError;

  async function updateEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave || processing) return;
    setProcessing("event-update");
    setMessage("Saving event details...");
    try {
      const updatedProject = await apiPatch<Project, { title: string; event_date?: string | null }>(`/projects/${currentProject.id}`, {
        title: title.trim(),
        event_date: eventDate || null
      });
      setCurrentProject(updatedProject);
      setTitle(updatedProject.title);
      setEventDate(updatedProject.event_date ?? "");
      setMessage("Event details updated.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update event.");
    } finally {
      setProcessing(null);
    }
  }

  async function archiveOrRestoreEvent(action: "archive" | "restore") {
    if (!canArchiveEvent || processing) return;
    const prompt = action === "archive" ? "Archive this event? It will leave active planning but keep history." : "Restore this event to active planning?";
    if (!window.confirm(prompt)) return;
    setProcessing(`event-${action}`);
    setMessage(action === "archive" ? "Archiving event..." : "Restoring event...");
    try {
      const updatedProject = await apiPost<Project, Record<string, never>>(`/projects/${currentProject.id}/${action}`, {});
      setCurrentProject(updatedProject);
      setTitle(updatedProject.title);
      setEventDate(updatedProject.event_date ?? "");
      setMessage(action === "archive" ? "Event archived. History is preserved." : "Event restored.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : `Could not ${action} event.`);
    } finally {
      setProcessing(null);
    }
  }

  return (
    <>
      <section className="hero compact">
        <p className="eyebrow">{currentProject.type} dashboard</p>
        <h1>{currentProject.title}</h1>
        <p>
          Role: {role.replaceAll("_", " ")} · Event date: {currentProject.event_date ?? "To be confirmed"}
        </p>
      </section>

      <RoleAwareNav role={role} projectId={currentProject.id} />

      <section className="grid twoColumns" id="overview">
        <article className="panel resourceCard">
          <p className="eyebrow">Overview</p>
          <h2>Coordination Snapshot</h2>
          <p>Status: {currentProject.status === "archived" ? "Archived — hidden from active planning" : "Active planning"}</p>
          <p>Use the tabs above to view live meetings, committee tasks, vendors, and budget areas allowed for your role.</p>
        </article>
        <BudgetPreview visibility={visibility} />
        <article className="panel actionPanel resourceCard">
          <p className="eyebrow">Event details</p>
          <h2>Edit this event</h2>
          {canEditEvent ? (
            <form className="stack" onSubmit={updateEvent}>
              <label className="formField">
                Event title
                <input value={title} onChange={(event) => setTitle(event.target.value)} aria-invalid={Boolean(titleError)} />
                <span className="helperText">At least 4 characters; visible to invited members.</span>
                {titleError ? <span className="errorText">{titleError}</span> : null}
              </label>
              <label className="formField">
                Event date
                <input value={eventDate} onChange={(event) => setEventDate(event.target.value)} type="date" />
                <span className="helperText">Optional. Leave blank if the ceremony date is not confirmed.</span>
              </label>
              <div className="buttonRow">
                <button className="primaryButton" data-icon="✓" disabled={!canSave || processing === "event-update"} type="submit">{processing === "event-update" ? "Saving..." : "Save event"}</button>
                {canArchiveEvent ? (
                  <button className="ghostButton danger" data-icon={currentProject.status === "archived" ? "↻" : "↓"} disabled={Boolean(processing)} type="button" onClick={() => void archiveOrRestoreEvent(currentProject.status === "archived" ? "restore" : "archive")}>
                    {processing === "event-archive" ? "Archiving..." : processing === "event-restore" ? "Restoring..." : currentProject.status === "archived" ? "Restore event" : "Archive event"}
                  </button>
                ) : null}
              </div>
            </form>
          ) : <p>Your role can view this event, but cannot edit event details.</p>}
          <p>{message}</p>
        </article>
      </section>
    </>
  );
}
