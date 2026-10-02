"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../lib/api";
import type { Communication, CommunicationAudience, CommunicationPriority, CommunicationSummary, CommunicationType, Project, ProjectRole } from "../lib/types";
import { useActiveProject } from "../lib/useActiveProject";
import { EventScopedHeader, EventWorkspaceGuard } from "./EventWorkspaceGuard";
import { StateBlock } from "./StateBlock";

type Member = { id: string; user_id: string; role: ProjectRole; user_name?: string | null; user_email?: string | null; permissions?: string[] };
type CommunicationFilters = { search: string; type: string; priority: string; author_user_id: string; status: "ACTIVE" | "ARCHIVED" | "ALL" };
type CommunicationForm = { title: string; body: string; communication_type: CommunicationType; priority: CommunicationPriority; audience_mode: CommunicationAudience; recipient_user_ids: string[] };

const emptyForm: CommunicationForm = { title: "", body: "", communication_type: "ANNOUNCEMENT", priority: "NORMAL", audience_mode: "ALL_MEMBERS", recipient_user_ids: [] };
const emptyFilters: CommunicationFilters = { search: "", type: "", priority: "", author_user_id: "", status: "ACTIVE" };
const types: Array<{ value: CommunicationType; label: string }> = [
  { value: "ANNOUNCEMENT", label: "Announcement" },
  { value: "UPDATE", label: "Update" },
  { value: "REMINDER", label: "Reminder" },
  { value: "PLANNING_NOTE", label: "Planning note" }
];
const priorities: Array<{ value: CommunicationPriority; label: string }> = [
  { value: "NORMAL", label: "Normal" },
  { value: "IMPORTANT", label: "Important" },
  { value: "URGENT", label: "Urgent" }
];

function titleCase(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value?: string | null) {
  if (!value) return "Date not available";
  return new Intl.DateTimeFormat("en-UG", { dateStyle: "medium", timeStyle: "short", timeZone: "Africa/Kampala" }).format(new Date(value));
}

function canManage(project?: Project | null) {
  return Boolean(project && (["OWNER", "PARTNER", "COMMITTEE_CHAIR"] as ProjectRole[]).includes(project.role ?? "FAMILY_VIEWER") || project?.permissions?.includes("communications.manage"));
}

function buildQuery(filters: CommunicationFilters) {
  const params = new URLSearchParams();
  if (filters.search.trim()) params.set("search", filters.search.trim());
  if (filters.type) params.set("type", filters.type);
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.author_user_id) params.set("author_user_id", filters.author_user_id);
  if (filters.status !== "ACTIVE") params.set("status", filters.status);
  const query = params.toString();
  return query ? `?${query}` : "";
}

function normalizeError(error: unknown) {
  return error instanceof Error ? error.message : "We could not complete that request.";
}

export function CommunicationsClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [communications, setCommunications] = useState<Communication[]>([]);
  const [summary, setSummary] = useState<CommunicationSummary | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [filters, setFilters] = useState<CommunicationFilters>(emptyFilters);
  const [form, setForm] = useState<CommunicationForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [notice, setNotice] = useState("Updates are visible only to the event members they are meant for.");
  const [processing, setProcessing] = useState<string | null>(null);

  const load = useCallback(async (activeProject: Project, nextFilters: CommunicationFilters) => {
    const [nextCommunications, nextSummary, nextMembers] = await Promise.all([
      apiGet<Communication[]>(`/projects/${activeProject.id}/communications${buildQuery(nextFilters)}`),
      apiGet<CommunicationSummary>(`/projects/${activeProject.id}/communications/summary`),
      apiGet<Member[]>(`/projects/${activeProject.id}/members`)
    ]);
    setCommunications(nextCommunications);
    setSummary(nextSummary);
    setMembers(nextMembers);
  }, []);

  useEffect(() => {
    if (!project) {
      setCommunications([]);
      setSummary(null);
      setMembers([]);
      return;
    }
    void load(project, filters).catch((error) => {
      setCommunications([]);
      setSummary(null);
      setNotice(normalizeError(error));
    });
  }, [project, filters, load]);

  const eligibleMembers = useMemo(() => members.filter((member) => member.role !== "GUEST_VIEWER"), [members]);
  const planningMembers = useMemo(() => eligibleMembers.filter((member) => member.role !== "FAMILY_VIEWER"), [eligibleMembers]);
  const selectableMembers = form.communication_type === "PLANNING_NOTE" ? planningMembers : eligibleMembers;
  const manageable = canManage(project);
  const titleError = form.title.trim() && form.title.trim().length < 3 ? "Title must be at least 3 characters." : "";
  const bodyError = form.body.trim() ? "" : "Write a short message for the planning team.";
  const selectionError = form.audience_mode === "SELECTED_MEMBERS" && form.recipient_user_ids.length === 0 ? "Select at least one recipient." : "";
  const canSubmit = Boolean(project && manageable && form.title.trim().length >= 3 && !titleError && !bodyError && !selectionError && !processing);

  function updateForm<K extends keyof CommunicationForm>(key: K, value: CommunicationForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function toggleRecipient(userId: string) {
    setForm((current) => ({ ...current, recipient_user_ids: current.recipient_user_ids.includes(userId) ? current.recipient_user_ids.filter((id) => id !== userId) : [...current.recipient_user_ids, userId] }));
  }

  function startEdit(item: Communication) {
    setEditingId(item.id);
    setForm({ title: item.title, body: item.body, communication_type: item.communication_type, priority: item.priority, audience_mode: item.audience_mode, recipient_user_ids: item.recipient_user_ids });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmit) return;
    setProcessing(editingId ? `edit-${editingId}` : "create");
    setNotice(editingId ? "Saving communication..." : "Publishing communication...");
    try {
      if (editingId) {
        await apiPatch<Communication, Pick<CommunicationForm, "title" | "body" | "communication_type" | "priority">>(`/projects/${project.id}/communications/${editingId}`, { title: form.title.trim(), body: form.body.trim(), communication_type: form.communication_type, priority: form.priority });
      } else {
        await apiPost<Communication, CommunicationForm>(`/projects/${project.id}/communications`, { ...form, title: form.title.trim(), body: form.body.trim() });
      }
      resetForm();
      setNotice(editingId ? "Communication updated." : "Communication published for the selected audience.");
      await load(project, filters);
    } catch (error) {
      setNotice(normalizeError(error));
    } finally {
      setProcessing(null);
    }
  }

  async function mutate(item: Communication, action: "read" | "pin" | "unpin" | "archive") {
    if (!project || processing) return;
    if (action === "archive" && !window.confirm("Archive this communication? It will remain available in history.")) return;
    setProcessing(`${action}-${item.id}`);
    try {
      await apiPost<Communication, Record<string, never>>(`/projects/${project.id}/communications/${item.id}/${action}`, {});
      setNotice(action === "read" ? "Marked as read." : action === "archive" ? "Communication archived." : action === "pin" ? "Communication pinned." : "Communication unpinned.");
      await load(project, filters);
    } catch (error) {
      setNotice(normalizeError(error));
    } finally {
      setProcessing(null);
    }
  }

  if (state !== "ready") return <EventWorkspaceGuard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;
  if (!project) return <StateBlock title="Choose an event" message="Open an event to view its communications." />;

  return (
    <>
      <EventScopedHeader projects={projects} project={project} onSelect={selectProject} />
      <section className="grid fourColumns">
        <article className="metric"><span>Unread</span><strong>{summary?.unread_count ?? 0}</strong><p>Updates waiting for your attention</p></article>
        <article className="metric"><span>Active updates</span><strong>{summary?.total_active ?? 0}</strong><p>Visible to your event role</p></article>
        <article className="metric"><span>Pinned</span><strong>{summary?.pinned_count ?? 0}</strong><p>Important messages kept close</p></article>
        <article className="metric"><span>Audience</span><strong>{manageable ? "Team" : "Member"}</strong><p>{manageable ? "You can publish updates" : "You can read eligible updates"}</p></article>
      </section>

      <section className="grid twoColumns">
        <article className="panel resourceCard overviewPanel">
          <p className="eyebrow">Event communications</p>
          <h2>{editingId ? "Edit communication" : "Share an update"}</h2>
          {manageable ? (
            <form className="stack" onSubmit={save}>
              <label className="formField">Title<input value={form.title} onChange={(event) => updateForm("title", event.target.value)} placeholder="Final family meeting details" aria-invalid={Boolean(titleError)} />{titleError ? <span className="errorText">{titleError}</span> : null}</label>
              <label className="formField">Message<textarea value={form.body} onChange={(event) => updateForm("body", event.target.value)} placeholder="Share the decision, reminder, or planning detail..." aria-invalid={Boolean(bodyError)} />{bodyError ? <span className="errorText">{bodyError}</span> : null}</label>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Type<select value={form.communication_type} onChange={(event) => { const nextType = event.target.value as CommunicationType; updateForm("communication_type", nextType); if (nextType === "PLANNING_NOTE" && form.recipient_user_ids.some((id) => !planningMembers.some((member) => member.user_id === id))) updateForm("recipient_user_ids", []); }}>{types.map((type) => <option value={type.value} key={type.value}>{type.label}</option>)}</select></label>
                <label className="formField">Priority<select value={form.priority} onChange={(event) => updateForm("priority", event.target.value as CommunicationPriority)}>{priorities.map((priority) => <option value={priority.value} key={priority.value}>{priority.label}</option>)}</select></label>
              </div>
              {!editingId ? <>
                <label className="formField">Audience<select value={form.audience_mode} onChange={(event) => updateForm("audience_mode", event.target.value as CommunicationAudience)}><option value="ALL_MEMBERS">Eligible event members</option><option value="SELECTED_MEMBERS">Selected members only</option></select></label>
                {form.audience_mode === "SELECTED_MEMBERS" ? <div className="stack"><span className="helperText">{form.communication_type === "PLANNING_NOTE" ? "Planning notes are limited to the planning team." : "Choose members from this event only."}</span>{selectableMembers.map((member) => <label className="checkboxField" key={member.user_id}><input type="checkbox" checked={form.recipient_user_ids.includes(member.user_id)} onChange={() => toggleRecipient(member.user_id)} /><span>{member.user_name || member.user_email || member.user_id} · {titleCase(member.role)}</span></label>)}{selectionError ? <span className="errorText">{selectionError}</span> : null}</div> : <p className="helperText">Family viewers can see regular announcements; guest viewers do not receive internal communications.</p>}
              </> : <p className="helperText">Audience stays fixed after publishing so the communication history remains clear.</p>}
              <div className="buttonRow"><button className="primaryButton" disabled={!canSubmit} type="submit">{processing ? "Saving..." : editingId ? "Save changes" : "Publish update"}</button>{editingId ? <button className="ghostButton" type="button" onClick={resetForm}>Cancel</button> : null}</div>
            </form>
          ) : <p>You can read communications shared with your event role. Publishing and editing are reserved for event leads and explicitly authorized coordinators.</p>}
          <p>{notice}</p>
        </article>

        <article className="panel resourceCard attentionPanel">
          <p className="eyebrow">Recent attention</p>
          <h2>Keep the team aligned</h2>
          {summary?.recent.length ? <div className="attentionList">{summary.recent.slice(0, 3).map((item) => <button className="attentionItem" type="button" key={item.id} onClick={() => void mutate(item, "read")}><strong>{item.title}</strong><span>{item.is_read ? `${titleCase(item.communication_type)} · ${formatDate(item.created_at)}` : "Unread · open to mark as read"}</span></button>)}</div> : <p>No communications yet. Publish the first event update when the planning team has something important to share.</p>}
        </article>
      </section>

      <section className="panel tablePanel">
        <div className="sectionHeaderRow"><div><p className="eyebrow">Communication history</p><h2>{filters.status === "ARCHIVED" ? "Archived history" : "Updates for this event"}</h2></div><span className="badge softBadge">{communications.length} shown</span></div>
        <div className="filterGrid">
          <label className="formField">Search<input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Search title or message" /></label>
          <label className="formField">Type<select value={filters.type} onChange={(event) => setFilters((current) => ({ ...current, type: event.target.value }))}><option value="">All types</option>{types.map((type) => <option value={type.value} key={type.value}>{type.label}</option>)}</select></label>
          <label className="formField">Priority<select value={filters.priority} onChange={(event) => setFilters((current) => ({ ...current, priority: event.target.value }))}><option value="">All priorities</option>{priorities.map((priority) => <option value={priority.value} key={priority.value}>{priority.label}</option>)}</select></label>
          <label className="formField">Author<select value={filters.author_user_id} onChange={(event) => setFilters((current) => ({ ...current, author_user_id: event.target.value }))}><option value="">All authors</option>{members.filter((member) => member.role !== "GUEST_VIEWER").map((member) => <option value={member.user_id} key={member.user_id}>{member.user_name || member.user_email || member.user_id}</option>)}</select></label>
          <label className="formField">View<select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value as CommunicationFilters["status"] }))}><option value="ACTIVE">Active updates</option><option value="ARCHIVED">Archived history</option><option value="ALL">All history</option></select></label>
          <button className="ghostButton" type="button" onClick={() => setFilters(emptyFilters)}>Clear filters</button>
        </div>
        {communications.length ? <div className="stack communicationList">{communications.map((item) => <article className={`panel communicationCard${item.is_read ? "" : " unreadCommunication"}`} key={item.id}><div className="sectionHeaderRow"><div><div className="planningAreaList"><span className={item.priority === "URGENT" ? "badge warningBadge" : item.priority === "IMPORTANT" ? "badge successBadge" : "badge softBadge"}>{titleCase(item.priority)}</span><span className="badge softBadge">{titleCase(item.communication_type)}</span>{item.audience_mode === "SELECTED_MEMBERS" ? <span className="badge softBadge">Targeted</span> : null}{item.is_pinned ? <span className="badge successBadge">Pinned</span> : null}{item.is_archived ? <span className="badge warningBadge">Archived</span> : null}</div><h3>{item.title}</h3></div><span className="helperText">{formatDate(item.created_at)}</span></div><p className="communicationBody">{item.body}</p><p className="helperText">By {item.author_name || item.author_email || "Event team"} · Updated {formatDate(item.updated_at)}</p><div className="buttonRow tableActions">{!item.is_read ? <button className="ghostButton" type="button" disabled={Boolean(processing)} onClick={() => void mutate(item, "read")}>Mark as read</button> : null}{manageable && !item.is_archived ? <><button className="ghostButton" type="button" disabled={Boolean(processing)} onClick={() => startEdit(item)}>Edit</button><button className="ghostButton" type="button" disabled={Boolean(processing)} onClick={() => void mutate(item, item.is_pinned ? "unpin" : "pin")}>{item.is_pinned ? "Unpin" : "Pin"}</button><button className="ghostButton danger" type="button" disabled={Boolean(processing)} onClick={() => void mutate(item, "archive")}>Archive</button></> : null}</div></article>)}</div> : <StateBlock title={filters.status === "ARCHIVED" ? "No archived communications" : "No communications yet"} message={filters.status === "ARCHIVED" ? "Archived updates will remain available here as part of the event history." : manageable ? "Publish the first update to keep your planning team aligned." : "Updates shared with your event role will appear here."} />}
      </section>
    </>
  );
}
