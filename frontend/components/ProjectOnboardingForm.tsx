"use client";

import { FormEvent, useMemo, useState } from "react";
import { apiPost } from "../lib/api";
import type { EventType, Project } from "../lib/types";

type ProjectPayload = {
  type: EventType;
  title: string;
  event_date?: string | null;
};

export function ProjectOnboardingForm({ onCreated }: { onCreated?: (project: Project) => void }) {
  const [type, setType] = useState<EventType>("wedding");
  const [title, setTitle] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [message, setMessage] = useState("Create your first private event workspace.");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const titleError = title && title.trim().length < 4 ? "Event title must be at least 4 characters." : "";
  const dateError = eventDate && eventDate < new Date().toISOString().slice(0, 10) ? "Event date cannot be in the past." : "";
  const isValid = useMemo(() => title.trim().length >= 4 && !titleError && !dateError, [title, titleError, dateError]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid || isSubmitting) return;

    setIsSubmitting(true);
    setMessage("Creating your event workspace...");
    try {
      const payload: ProjectPayload = { type, title: title.trim(), event_date: eventDate || null };
      const project = await apiPost<Project, ProjectPayload>("/projects", payload);
      setMessage("Event created. You can now add meetings, committee tasks, vendors, and budgets.");
      setTitle("");
      setEventDate("");
      onCreated?.(project);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create the event.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <article className="panel actionPanel">
      <p className="eyebrow">Start Here</p>
      <h2>Create an event workspace</h2>
      <p className="helperText">Best for couples, planners, or family leads starting a wedding or introduction ceremony.</p>
      <form className="stack" onSubmit={submit}>
        <label className="formField">
          Event type
          <select value={type} onChange={(event) => setType(event.target.value as EventType)}>
            <option value="wedding">Wedding</option>
            <option value="introduction">Introduction</option>
            <option value="linked">Linked ceremonies</option>
          </select>
          <span className="helperText">Choose the ceremony model closest to your planning workflow.</span>
        </label>
        <label className="formField">
          Event title
          <input value={title} onBlur={() => setTouched((current) => ({ ...current, title: true }))} onChange={(event) => setTitle(event.target.value)} placeholder="Amina & David Wedding" aria-invalid={Boolean(titleError)} />
          <span className="helperText">At least 4 characters; visible to invited members.</span>
          {touched.title && titleError ? <span className="errorText">{titleError}</span> : null}
        </label>
        <label className="formField">
          Event date
          <input value={eventDate} onBlur={() => setTouched((current) => ({ ...current, eventDate: true }))} onChange={(event) => setEventDate(event.target.value)} type="date" aria-invalid={Boolean(dateError)} />
          <span className="helperText">Optional, but useful for reminders and committee planning.</span>
          {touched.eventDate && dateError ? <span className="errorText">{dateError}</span> : null}
        </label>
        <button className="primaryButton" disabled={!isValid || isSubmitting} type="submit">{isSubmitting ? "Creating..." : "Create event"}</button>
      </form>
      <p>{message}</p>
    </article>
  );
}
