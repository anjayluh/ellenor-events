"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../lib/api";
import type { Project, TimelineAssignee, TimelineItem, TimelineStatus, TimelineSummary } from "../lib/types";
import { useActiveProject } from "../lib/useActiveProject";
import { EventScopedHeader, EventWorkspaceGuard } from "./EventWorkspaceGuard";
import { StateBlock } from "./StateBlock";

type TimelineForm = {
  title: string;
  description: string;
  category: string;
  start_at: string;
  end_at: string;
  location: string;
  assignee_user_id: string;
  status: TimelineStatus;
  notes: string;
  sort_order: string;
};
type TimelineFilters = { search: string; category: string; status: string; assignee: string; date: string; mode: "all" | "today" | "upcoming" | "completed" | "cancelled" | "conflicts" };
type TimelinePayload = {
  title: string;
  description: string | null;
  category: string;
  start_at: string;
  end_at: string;
  location: string | null;
  assignee_user_id: string | null;
  status: TimelineStatus;
  notes: string | null;
  sort_order: number;
};

const categories = ["PREPARATION", "CEREMONY", "RECEPTION", "FAMILY", "PHOTOGRAPHY", "VIDEOGRAPHY", "CATERING", "DECOR", "ENTERTAINMENT", "TRANSPORT", "GUESTS", "VENDORS", "PROGRAM", "BREAK", "OTHER"];
const statuses: TimelineStatus[] = ["UPCOMING", "IN_PROGRESS", "COMPLETED", "CANCELLED"];
const emptyForm: TimelineForm = { title: "", description: "", category: "PROGRAM", start_at: "", end_at: "", location: "", assignee_user_id: "", status: "UPCOMING", notes: "", sort_order: "0" };
const emptyFilters: TimelineFilters = { search: "", category: "", status: "", assignee: "", date: "", mode: "all" };

function canManageTimeline(project?: Project | null) {
  return Boolean(project?.role === "OWNER" || project?.role === "PARTNER" || project?.role === "COMMITTEE_CHAIR" || project?.permissions?.includes("tasks.manage"));
}

function titleCase(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-UG", { dateStyle: "medium", timeStyle: "short", timeZone: "Africa/Kampala" }).format(new Date(value));
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en-UG", { hour: "numeric", minute: "2-digit", timeZone: "Africa/Kampala" }).format(new Date(value));
}

function dateInput(value: Date) {
  return value.toISOString().slice(0, 10);
}

function toDateTimeLocal(value: string) {
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function localToIso(value: string) {
  return new Date(value).toISOString();
}

function buildQuery(filters: TimelineFilters) {
  const params = new URLSearchParams();
  if (filters.search.trim()) params.set("search", filters.search.trim());
  if (filters.category.trim()) params.set("category", filters.category.trim());
  if (filters.assignee.trim()) params.set("assignee", filters.assignee.trim());
  if (filters.date.trim()) params.set("date", filters.date.trim());
  if (filters.mode === "today") params.set("today", "true");
  if (filters.mode === "upcoming") params.set("upcoming", "true");
  if (filters.mode === "completed") params.set("completed", "true");
  if (filters.mode === "cancelled") params.set("status", "CANCELLED");
  if (filters.mode === "conflicts") params.set("conflicts", "true");
  if (filters.status.trim()) params.set("status", filters.status.trim());
  const query = params.toString();
  return query ? `?${query}` : "";
}

function normalizeApiMessage(error: unknown) {
  return error instanceof Error ? error.message : "We could not complete that request.";
}

function toPayload(form: TimelineForm): TimelinePayload {
  return {
    title: form.title.trim(),
    description: form.description.trim() || null,
    category: form.category,
    start_at: localToIso(form.start_at),
    end_at: localToIso(form.end_at),
    location: form.location.trim() || null,
    assignee_user_id: form.assignee_user_id || null,
    status: form.status,
    notes: form.notes.trim() || null,
    sort_order: Number(form.sort_order || 0)
  };
}

function formFromItem(item: TimelineItem): TimelineForm {
  return {
    title: item.title,
    description: item.description ?? "",
    category: item.category,
    start_at: toDateTimeLocal(item.start_at),
    end_at: toDateTimeLocal(item.end_at),
    location: item.location ?? "",
    assignee_user_id: item.assignee_user_id ?? "",
    status: item.stored_status,
    notes: item.notes ?? "",
    sort_order: String(item.sort_order ?? 0)
  };
}

function assigneeLabel(assignee: TimelineAssignee) {
  return assignee.name || assignee.email || assignee.user_id;
}

export function TimelineClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [summary, setSummary] = useState<TimelineSummary | null>(null);
  const [assignees, setAssignees] = useState<TimelineAssignee[]>([]);
  const [filters, setFilters] = useState<TimelineFilters>(emptyFilters);
  const [form, setForm] = useState<TimelineForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [notice, setNotice] = useState("Plan the order, timing and responsibilities for everything happening around this event.");
  const [processing, setProcessing] = useState<string | null>(null);

  const loadTimeline = useCallback(async (activeProject: Project, nextFilters: TimelineFilters) => {
    const [nextItems, nextSummary, nextAssignees] = await Promise.all([
      apiGet<TimelineItem[]>(`/projects/${activeProject.id}/timeline${buildQuery(nextFilters)}`),
      apiGet<TimelineSummary>(`/projects/${activeProject.id}/timeline/summary`),
      apiGet<TimelineAssignee[]>(`/projects/${activeProject.id}/timeline/assignees`)
    ]);
    setItems(nextItems);
    setSummary(nextSummary);
    setAssignees(nextAssignees);
  }, []);

  useEffect(() => {
    if (!project) {
      setItems([]);
      setSummary(null);
      setAssignees([]);
      return;
    }
    void loadTimeline(project, filters).catch((error) => {
      setItems([]);
      setSummary(null);
      setNotice(normalizeApiMessage(error));
    });
  }, [project, filters, loadTimeline]);

  const canManage = canManageTimeline(project);
  const titleError = form.title && form.title.trim().length < 3 ? "Timeline title must be at least 3 characters." : "";
  const timeError = form.start_at && form.end_at && new Date(form.end_at).getTime() <= new Date(form.start_at).getTime() ? "End time must be after start time." : "";
  const canSubmit = Boolean(project && canManage && form.title.trim().length >= 3 && form.start_at && form.end_at && !titleError && !timeError && !processing);
  const nextItem = summary?.current_item ?? summary?.next_item ?? null;
  const visibleDates = useMemo(() => [...new Set(items.map((item) => item.start_at.slice(0, 10)))], [items]);

  async function saveItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmit) return;
    setProcessing(editingId ? `update-${editingId}` : "create");
    setNotice(editingId ? "Saving timeline item..." : "Adding timeline item...");
    try {
      const saved = editingId
        ? await apiPatch<TimelineItem, TimelinePayload>(`/projects/${project.id}/timeline/${editingId}`, toPayload(form))
        : await apiPost<TimelineItem, TimelinePayload>(`/projects/${project.id}/timeline`, toPayload(form));
      setForm(emptyForm);
      setEditingId(null);
      setNotice(saved.has_conflict ? "Timeline item saved. It overlaps with another schedule item, so review the conflict warning." : "Timeline item saved.");
      await loadTimeline(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  function startEdit(item: TimelineItem) {
    setEditingId(item.id);
    setForm(formFromItem(item));
  }

  async function quickStatus(item: TimelineItem, nextStatus: TimelineStatus) {
    if (!project || processing) return;
    setProcessing(`status-${item.id}`);
    setNotice("Updating timeline status...");
    try {
      await apiPatch<TimelineItem, { status: TimelineStatus }>(`/projects/${project.id}/timeline/${item.id}`, { status: nextStatus });
      setNotice(nextStatus === "COMPLETED" ? "Timeline item marked complete." : nextStatus === "CANCELLED" ? "Timeline item cancelled." : "Timeline item reopened.");
      await loadTimeline(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  async function deleteItem(itemId: string) {
    if (!project || processing || !window.confirm("Delete this timeline item?")) return;
    setProcessing(`delete-${itemId}`);
    setNotice("Deleting timeline item...");
    try {
      await apiDelete<{ status: string }>(`/projects/${project.id}/timeline/${itemId}`);
      setNotice("Timeline item deleted.");
      await loadTimeline(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  function shiftDate(days: number) {
    const base = filters.date ? new Date(`${filters.date}T00:00:00`) : new Date();
    base.setDate(base.getDate() + days);
    setFilters((current) => ({ ...current, date: dateInput(base), mode: "all" }));
  }

  if (state !== "ready") return <EventWorkspaceGuard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;
  if (!project) return <StateBlock title="Choose an event" message="Open an event to manage its timeline." />;

  return (
    <>
      <EventScopedHeader projects={projects} project={project} onSelect={selectProject} />
      <section className="grid fourColumns">
        <article className="metric"><span>Total items</span><strong>{summary?.total ?? 0}</strong><p>{summary?.today ?? 0} happening today</p></article>
        <article className="metric"><span>Upcoming</span><strong>{summary?.upcoming ?? 0}</strong><p>{summary?.in_progress ?? 0} in progress now</p></article>
        <article className="metric"><span>Completed</span><strong>{summary?.completed ?? 0}</strong><p>{summary?.cancelled ?? 0} cancelled</p></article>
        <article className="metric"><span>Conflicts</span><strong>{summary?.conflicts ?? 0}</strong><p>{summary?.conflicts ? "Review overlaps before the event" : "No overlaps detected"}</p></article>
      </section>

      <section className="grid twoColumns">
        <article className="panel resourceCard overviewPanel">
          <p className="eyebrow">Next up</p>
          {nextItem ? (
            <div className="stack">
              <h2>{nextItem.title}</h2>
              <p>{formatDateTime(nextItem.start_at)} · {nextItem.location ?? "Location to be confirmed"}</p>
              <div className="planningAreaList"><span className="badge successBadge">{titleCase(nextItem.status)}</span><span className="badge softBadge">{titleCase(nextItem.category)}</span>{nextItem.assignee_name ? <span className="badge softBadge">{nextItem.assignee_name}</span> : null}</div>
            </div>
          ) : <p>No current or upcoming timeline item is visible yet. Add the first activity to start building the event-day rhythm.</p>}
          {summary?.conflicts ? <p className="errorText">{summary.conflicts} schedule item{summary.conflicts === 1 ? "" : "s"} overlap. Overlaps are allowed, but review them intentionally.</p> : null}
        </article>

        <article className="panel actionPanel">
          <p className="eyebrow">Timeline item</p>
          <h2>{editingId ? "Edit schedule item" : "Add Timeline Item"}</h2>
          {canManage ? (
            <form className="stack" onSubmit={saveItem}>
              <label className="formField">Title<input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="Introduction ceremony" aria-invalid={Boolean(titleError)} />{titleError ? <span className="errorText">{titleError}</span> : <span className="helperText">Required. Name the activity clearly for the whole planning team.</span>}</label>
              <label className="formField">Description<textarea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="What happens during this activity?" /></label>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Category<select value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}>{categories.map((category) => <option key={category} value={category}>{titleCase(category)}</option>)}</select></label>
                <label className="formField">Status<select value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value as TimelineStatus }))}>{statuses.map((status) => <option key={status} value={status}>{titleCase(status)}</option>)}</select></label>
              </div>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Start<input type="datetime-local" value={form.start_at} onChange={(event) => setForm((current) => ({ ...current, start_at: event.target.value }))} /></label>
                <label className="formField">End<input type="datetime-local" value={form.end_at} onChange={(event) => setForm((current) => ({ ...current, end_at: event.target.value }))} aria-invalid={Boolean(timeError)} />{timeError ? <span className="errorText">{timeError}</span> : null}</label>
              </div>
              <label className="formField">Location<input value={form.location} onChange={(event) => setForm((current) => ({ ...current, location: event.target.value }))} placeholder="Bride's home, church, reception venue..." /></label>
              <label className="formField">Assignee<select value={form.assignee_user_id} onChange={(event) => setForm((current) => ({ ...current, assignee_user_id: event.target.value }))}><option value="">Unassigned</option>{assignees.map((assignee) => <option key={assignee.user_id} value={assignee.user_id}>{assigneeLabel(assignee)} · {titleCase(assignee.role)}</option>)}</select></label>
              <div className="grid twoColumns compactGrid"><label className="formField">Sort order<input inputMode="numeric" value={form.sort_order} onChange={(event) => setForm((current) => ({ ...current, sort_order: event.target.value }))} /></label><label className="formField">Notes<input value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Private coordination notes" /></label></div>
              <div className="buttonRow"><button className="primaryButton" data-icon="✓" disabled={!canSubmit} type="submit">{processing?.startsWith("update") ? "Saving..." : editingId ? "Save changes" : "Add item"}</button>{editingId ? <button className="ghostButton" data-icon="×" disabled={Boolean(processing)} type="button" onClick={() => { setEditingId(null); setForm(emptyForm); }}>Cancel</button> : null}</div>
            </form>
          ) : <p>You can view this event timeline, but editing is limited to event owners and authorized coordinators.</p>}
          <p>{notice}</p>
        </article>
      </section>

      <section className="panel tablePanel">
        <div className="sectionHeaderRow"><div><p className="eyebrow">Event schedule</p><h2>Chronological timeline</h2></div><div className="buttonRow"><button className="ghostButton" type="button" onClick={() => shiftDate(-1)}>Previous day</button><button className="ghostButton" type="button" onClick={() => setFilters((current) => ({ ...current, date: dateInput(new Date()), mode: "today" }))}>Today</button><button className="ghostButton" type="button" onClick={() => shiftDate(1)}>Next day</button></div></div>
        <div className="filterGrid">
          <label className="formField">Search<input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Search title, location, notes" /></label>
          <label className="formField">Date<input type="date" value={filters.date} onChange={(event) => setFilters((current) => ({ ...current, date: event.target.value, mode: "all" }))} /></label>
          <label className="formField">View<select value={filters.mode} onChange={(event) => setFilters((current) => ({ ...current, mode: event.target.value as TimelineFilters["mode"] }))}><option value="all">All Schedule</option><option value="today">Today</option><option value="upcoming">Upcoming</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option><option value="conflicts">Conflicts</option></select></label>
          <label className="formField">Category<select value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}><option value="">All categories</option>{categories.map((category) => <option key={category} value={category}>{titleCase(category)}</option>)}</select></label>
          <label className="formField">Assignee<select value={filters.assignee} onChange={(event) => setFilters((current) => ({ ...current, assignee: event.target.value }))}><option value="">All assignees</option>{assignees.map((assignee) => <option key={assignee.user_id} value={assignee.user_id}>{assigneeLabel(assignee)}</option>)}</select></label>
          <button className="ghostButton" data-icon="×" type="button" onClick={() => setFilters(emptyFilters)}>Clear filters</button>
        </div>

        {visibleDates.length ? <p className="helperText">Showing {items.length} item{items.length === 1 ? "" : "s"} across {visibleDates.length} schedule date{visibleDates.length === 1 ? "" : "s"}.</p> : null}
        {items.length ? (
          <div className="timelineList">
            {items.map((item) => (
              <article className={item.has_conflict ? "timelineItem conflictItem" : "timelineItem"} key={item.id}>
                <div className="timelineTime"><strong>{formatTime(item.start_at)}</strong><span>{item.duration_minutes} min</span></div>
                <div className="timelineContent">
                  <div className="sectionHeaderRow"><div><h3>{item.title}</h3><p>{formatDateTime(item.start_at)} – {formatTime(item.end_at)} · {item.location ?? "Location to be confirmed"}</p></div><span className={item.status === "COMPLETED" ? "badge successBadge" : item.has_conflict ? "badge warningBadge" : "badge softBadge"}>{titleCase(item.status)}</span></div>
                  <div className="planningAreaList"><span className="badge softBadge">{titleCase(item.category)}</span>{item.assignee_name || item.assignee_email ? <span className="badge softBadge">Assigned to {item.assignee_name ?? item.assignee_email}</span> : <span className="badge softBadge">Unassigned</span>}</div>
                  {item.description ? <p>{item.description}</p> : null}
                  {item.notes ? <p className="helperText">Notes: {item.notes}</p> : null}
                  {item.has_conflict ? <p className="errorText">Overlaps with {item.conflicts.map((conflict) => conflict.title).join(", ")}. Review timing before the event.</p> : null}
                  <div className="buttonRow tableActions">
                    {canManage ? <><button className="ghostButton" data-icon="✎" disabled={Boolean(processing)} type="button" onClick={() => startEdit(item)}>Edit</button>{item.status === "COMPLETED" || item.status === "CANCELLED" ? <button className="ghostButton" data-icon="↻" disabled={Boolean(processing)} type="button" onClick={() => void quickStatus(item, "UPCOMING")}>Reopen</button> : <button className="ghostButton" data-icon="✓" disabled={Boolean(processing)} type="button" onClick={() => void quickStatus(item, "COMPLETED")}>Mark complete</button>}<button className="ghostButton" data-icon="−" disabled={Boolean(processing)} type="button" onClick={() => void quickStatus(item, "CANCELLED")}>Cancel</button><button className="ghostButton danger" data-icon="×" disabled={Boolean(processing)} type="button" onClick={() => void deleteItem(item.id)}>{processing === `delete-${item.id}` ? "Deleting..." : "Delete"}</button></> : <span className="helperText">View only</span>}
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : <StateBlock title={filters.date ? "Nothing scheduled for this day" : "No timeline items yet"} message="Build your event schedule by adding the first activity." />}
      </section>
    </>
  );
}
