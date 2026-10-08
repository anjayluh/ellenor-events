"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../lib/api";
import { useActiveProject } from "../lib/useActiveProject";
import type { Meeting, MeetingAgendaItem, MeetingDecision, MeetingSummary, Project, ProjectRole } from "../lib/types";
import { ActiveEventSwitcher } from "./ActiveEventSwitcher";
import { RoleAwareNav } from "./RoleAwareNav";
import { StateBlock } from "./StateBlock";

type MemberOption = { user_id: string; user_name?: string | null; user_email?: string | null; role: ProjectRole };
type MeetingForm = { title: string; category: string; start_at: string; end_at: string; location: string; meeting_link: string; description: string; agenda: string };

const MANAGER_ROLES: ProjectRole[] = ["OWNER", "PARTNER", "COMMITTEE_CHAIR", "COMMITTEE_MEMBER"];
const categories = ["PLANNING", "FAMILY", "COMMITTEE", "BUDGET", "VENDOR", "GUESTS", "TIMELINE", "OTHER"];

const emptyForm: MeetingForm = { title: "", category: "PLANNING", start_at: "", end_at: "", location: "", meeting_link: "", description: "", agenda: "" };

function localValue(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function displayDate(value: string | null | undefined) {
  if (!value) return "Time to be confirmed";
  return new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function meetingForm(meeting?: Meeting): MeetingForm {
  return meeting ? {
    title: meeting.title,
    category: meeting.category || "PLANNING",
    start_at: localValue(meeting.start_at ?? meeting.scheduled_time),
    end_at: localValue(meeting.end_at),
    location: meeting.location ?? "",
    meeting_link: meeting.meeting_link ?? "",
    description: meeting.description ?? "",
    agenda: meeting.agenda ?? ""
  } : emptyForm;
}

function canManage(project?: Project | null) {
  return Boolean(project?.role && (MANAGER_ROLES.includes(project.role) || project.permissions?.includes("meetings.manage")));
}

function statusLabel(status: string) {
  return status.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function MeetingsWorkspace() {
  const { projects, project, state, message, selectProject } = useActiveProject();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [summary, setSummary] = useState<MeetingSummary | null>(null);
  const [members, setMembers] = useState<MemberOption[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<MeetingForm>(emptyForm);
  const [editing, setEditing] = useState(false);
  const [participantUserId, setParticipantUserId] = useState("");
  const [participantStatus, setParticipantStatus] = useState("INVITED");
  const [agendaTitle, setAgendaTitle] = useState("");
  const [decisionText, setDecisionText] = useState("");
  const [notes, setNotes] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDueDate, setTaskDueDate] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [processing, setProcessing] = useState<string | null>(null);
  const [error, setError] = useState("");

  const selectedMeeting = useMemo(() => meetings.find((meeting) => meeting.id === selectedId) ?? null, [meetings, selectedId]);

  async function loadWorkspace(activeProject: Project) {
    const [loadedMeetings, loadedSummary, loadedMembers] = await Promise.all([
      apiGet<Meeting[]>(`/projects/${activeProject.id}/meetings`),
      apiGet<MeetingSummary>(`/projects/${activeProject.id}/meetings/summary`),
      apiGet<Array<{ user_id: string; user_name?: string | null; user_email?: string | null; role: ProjectRole }>>(`/projects/${activeProject.id}/members`)
    ]);
    setMeetings(loadedMeetings);
    setSummary(loadedSummary);
    setMembers(loadedMembers);
    setSelectedId((current) => current && loadedMeetings.some((meeting) => meeting.id === current) ? current : loadedMeetings[0]?.id ?? null);
  }

  useEffect(() => {
    if (!project) return;
    void loadWorkspace(project).catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load meetings."));
  }, [project]);

  useEffect(() => {
    setForm(meetingForm(selectedMeeting ?? undefined));
    setNotes(selectedMeeting?.notes ?? "");
  }, [selectedMeeting]);

  const visibleMeetings = meetings.filter((meeting) => {
    if (filter === "UPCOMING") return meeting.status.toUpperCase() !== "COMPLETED" && meeting.status.toUpperCase() !== "CANCELLED" && new Date(meeting.start_at ?? meeting.scheduled_time).getTime() >= Date.now();
    if (filter === "COMPLETED") return meeting.status.toUpperCase() === "COMPLETED" || meeting.status.toLowerCase() === "completed";
    if (filter === "CANCELLED") return meeting.status.toUpperCase() === "CANCELLED" || meeting.status.toLowerCase() === "cancelled";
    if (filter === "CONFLICTS") return meeting.conflict_ids.length > 0;
    return true;
  });

  async function refresh() {
    if (!project) return;
    await loadWorkspace(project);
  }

  async function saveMeeting(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !form.title.trim() || !form.start_at || processing) return;
    setProcessing("meeting");
    setError("");
    const payload = {
      type: form.category.toLowerCase(),
      title: form.title.trim(),
      category: form.category,
      start_at: new Date(form.start_at).toISOString(),
      scheduled_time: new Date(form.start_at).toISOString(),
      end_at: form.end_at ? new Date(form.end_at).toISOString() : null,
      location: form.location.trim() || null,
      meeting_link: form.meeting_link.trim() || null,
      description: form.description.trim() || null,
      agenda: form.agenda.trim() || null
    };
    try {
      const saved = editing && selectedMeeting
        ? await apiPatch<Meeting, typeof payload>(`/projects/${project.id}/meetings/${selectedMeeting.id}`, payload)
        : await apiPost<Meeting, typeof payload>(`/projects/${project.id}/meetings`, payload);
      setSelectedId(saved.id);
      setEditing(false);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save meeting.");
    } finally {
      setProcessing(null);
    }
  }

  async function setMeetingStatus(action: "complete" | "cancel" | "reopen") {
    if (!project || !selectedMeeting || processing) return;
    setProcessing(action);
    try {
      const updated = await apiPost<Meeting, Record<string, never>>(`/projects/${project.id}/meetings/${selectedMeeting.id}/${action}`, {});
      setMeetings((current) => current.map((meeting) => meeting.id === updated.id ? updated : meeting));
      setSummary(await apiGet<MeetingSummary>(`/projects/${project.id}/meetings/summary`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not update meeting status.");
    } finally {
      setProcessing(null);
    }
  }

  async function addParticipant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !selectedMeeting || !participantUserId) return;
    setProcessing("participant");
    try {
      await apiPost(`/projects/${project.id}/meetings/${selectedMeeting.id}/participants`, { user_id: participantUserId, attendance_status: participantStatus });
      setParticipantUserId("");
      await refresh();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not add participant."); } finally { setProcessing(null); }
  }

  async function addAgenda(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !selectedMeeting || !agendaTitle.trim()) return;
    setProcessing("agenda");
    try {
      await apiPost(`/projects/${project.id}/meetings/${selectedMeeting.id}/agenda`, { title: agendaTitle.trim(), sort_order: selectedMeeting.agenda_items.length });
      setAgendaTitle("");
      await refresh();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not add agenda item."); } finally { setProcessing(null); }
  }

  async function addDecision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !selectedMeeting || !decisionText.trim()) return;
    setProcessing("decision");
    try {
      await apiPost(`/projects/${project.id}/meetings/${selectedMeeting.id}/decisions`, { decision_text: decisionText.trim() });
      setDecisionText("");
      await refresh();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not record decision."); } finally { setProcessing(null); }
  }

  async function saveNotes(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !selectedMeeting) return;
    setProcessing("notes");
    try { await apiPatch(`/projects/${project.id}/meetings/${selectedMeeting.id}/notes`, { notes }); await refresh(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Could not save notes."); }
    finally { setProcessing(null); }
  }

  async function addTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !selectedMeeting || !taskTitle.trim()) return;
    setProcessing("task");
    try {
      await apiPost(`/projects/${project.id}/meetings/${selectedMeeting.id}/tasks`, { title: taskTitle.trim(), due_date: taskDueDate || null, status: "TODO", priority: "MEDIUM", category: "COMMITTEE" });
      setTaskTitle("");
      setTaskDueDate("");
      await refresh();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not add follow-up task."); } finally { setProcessing(null); }
  }

  async function deleteMeeting() {
    if (!project || !selectedMeeting || processing || !window.confirm("Delete this meeting? Its linked collaboration records will also be removed.")) return;
    setProcessing("delete");
    try { await apiDelete(`/projects/${project.id}/meetings/${selectedMeeting.id}`); setSelectedId(null); await refresh(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Could not delete meeting."); }
    finally { setProcessing(null); }
  }

  if (state === "anonymous") return <StateBlock title="Sign in required" message="Sign in to continue to meetings." />;
  if (state === "loading") return <StateBlock title="Loading" message="Preparing the event meeting space." />;
  if (state === "empty") return <StateBlock title="Create your first event" message="Meetings become available once your event workspace is ready." />;
  if (state === "selection_required") return <StateBlock title="Choose an event" message={message || "Select an event workspace to view meetings."} />;
  if (state === "error" || !project) return <StateBlock title="Could not load meetings" message={message || error || "Please try again."} />;

  return (
    <div className="stack">
      <ActiveEventSwitcher projects={projects} activeProjectId={project.id} onChange={selectProject} />
      <RoleAwareNav role={project.role ?? "GUEST_VIEWER"} projectId={project.id} />
      {error ? <div className="errorText" role="alert">{error}</div> : null}
      <section className="grid fourColumns">
        {[{ label: "Total", value: summary?.total ?? meetings.length }, { label: "Today", value: summary?.today ?? 0 }, { label: "Upcoming", value: summary?.upcoming ?? 0 }, { label: "Conflicts", value: summary?.conflicts ?? 0 }].map((card) => <article className="panel summaryCard" key={card.label}><span>{card.label}</span><strong>{card.value}</strong></article>)}
      </section>
      <section className="grid twoColumns meetingWorkspaceGrid">
        <div className="stack">
          {canManage(project) && !editing ? <button className="primaryButton" type="button" onClick={() => { setSelectedId(null); setForm(emptyForm); setEditing(true); }}>+ Add timeline meeting</button> : null}
          <div className="buttonRow">
            {["ALL", "UPCOMING", "COMPLETED", "CANCELLED", "CONFLICTS"].map((value) => <button className={filter === value ? "primaryButton" : "ghostButton"} type="button" key={value} onClick={() => setFilter(value)}>{statusLabel(value)}</button>)}
          </div>
          {visibleMeetings.length ? visibleMeetings.map((meeting) => <button className={`panel meetingListItem ${selectedId === meeting.id ? "selected" : ""}`} type="button" key={meeting.id} onClick={() => { setSelectedId(meeting.id); setEditing(false); }}><span className="eyebrow">{meeting.category} · {statusLabel(meeting.status)}</span><strong>{meeting.title}</strong><span>{displayDate(meeting.start_at ?? meeting.scheduled_time)}{meeting.location ? ` · ${meeting.location}` : ""}</span>{meeting.conflict_ids.length ? <small className="errorText">Overlaps {meeting.conflict_ids.length} other item{meeting.conflict_ids.length === 1 ? "" : "s"}</small> : null}</button>) : <StateBlock title="No meetings yet" message="Create a meeting to give the team a shared place for agenda, decisions, and follow-up." />}
        </div>
        <div className="stack">
          {editing ? <article className="panel actionPanel"><p className="eyebrow">{selectedMeeting ? "Edit meeting" : "New meeting"}</p><form className="stack" onSubmit={saveMeeting}><label className="formField">Title<input required minLength={3} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label><div className="formGrid"><label className="formField">Category<select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>{categories.map((category) => <option key={category}>{category}</option>)}</select></label><label className="formField">Start<input required type="datetime-local" value={form.start_at} onChange={(event) => setForm({ ...form, start_at: event.target.value })} /></label><label className="formField">End<input type="datetime-local" value={form.end_at} onChange={(event) => setForm({ ...form, end_at: event.target.value })} /></label><label className="formField">Location<input value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} placeholder="Committee room or venue" /></label></div><label className="formField">Meeting link<input type="url" value={form.meeting_link} onChange={(event) => setForm({ ...form, meeting_link: event.target.value })} placeholder="Optional video link" /></label><label className="formField">Description<textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} rows={3} /></label><label className="formField">Agenda<textarea value={form.agenda} onChange={(event) => setForm({ ...form, agenda: event.target.value })} rows={3} /></label><div className="buttonRow"><button className="primaryButton" disabled={processing === "meeting"} type="submit">{processing === "meeting" ? "Saving..." : "Save meeting"}</button><button className="ghostButton" type="button" onClick={() => setEditing(false)}>Cancel</button></div></form></article> : selectedMeeting ? <MeetingDetail meeting={selectedMeeting} members={members} canEdit={canManage(project)} participantUserId={participantUserId} participantStatus={participantStatus} agendaTitle={agendaTitle} decisionText={decisionText} notes={notes} taskTitle={taskTitle} taskDueDate={taskDueDate} processing={processing} onEdit={() => setEditing(true)} onDelete={() => void deleteMeeting()} onStatus={setMeetingStatus} onParticipantSubmit={addParticipant} onParticipantUserChange={setParticipantUserId} onParticipantStatusChange={setParticipantStatus} onAgendaSubmit={addAgenda} onAgendaTitleChange={setAgendaTitle} onDecisionSubmit={addDecision} onDecisionTextChange={setDecisionText} onNotesChange={setNotes} onNotesSubmit={saveNotes} onTaskSubmit={addTask} onTaskTitleChange={setTaskTitle} onTaskDueDateChange={setTaskDueDate} /> : <StateBlock title="Choose a meeting" message="Select a meeting to view its participants, agenda, decisions, and follow-up tasks." />}
        </div>
      </section>
    </div>
  );
}

function MeetingDetail(props: { meeting: Meeting; members: MemberOption[]; canEdit: boolean; participantUserId: string; participantStatus: string; agendaTitle: string; decisionText: string; notes: string; taskTitle: string; taskDueDate: string; processing: string | null; onEdit: () => void; onDelete: () => void; onStatus: (action: "complete" | "cancel" | "reopen") => void; onParticipantSubmit: (event: FormEvent<HTMLFormElement>) => void; onParticipantUserChange: (value: string) => void; onParticipantStatusChange: (value: string) => void; onAgendaSubmit: (event: FormEvent<HTMLFormElement>) => void; onAgendaTitleChange: (value: string) => void; onDecisionSubmit: (event: FormEvent<HTMLFormElement>) => void; onDecisionTextChange: (value: string) => void; onNotesChange: (value: string) => void; onNotesSubmit: (event: FormEvent<HTMLFormElement>) => void; onTaskSubmit: (event: FormEvent<HTMLFormElement>) => void; onTaskTitleChange: (value: string) => void; onTaskDueDateChange: (value: string) => void }) {
  const { meeting } = props;
  return <article className="panel meetingDetailPanel"><div className="sectionHeaderRow"><div><p className="eyebrow">{meeting.category} · {statusLabel(meeting.status)}</p><h2>{meeting.title}</h2><p>{displayDate(meeting.start_at ?? meeting.scheduled_time)}{meeting.location ? ` · ${meeting.location}` : ""}</p></div>{props.canEdit ? <div className="buttonRow"><button className="ghostButton" type="button" onClick={props.onEdit}>Edit</button><button className="ghostButton danger" type="button" onClick={props.onDelete}>Delete</button></div> : null}</div>{meeting.conflict_ids.length ? <p className="errorText">This meeting overlaps {meeting.conflict_ids.length} other scheduled item{meeting.conflict_ids.length === 1 ? "" : "s"}. Review the timing before the event.</p> : null}<p>{meeting.description || "No description yet."}</p><div className="buttonRow">{props.canEdit && meeting.status.toUpperCase() !== "COMPLETED" ? <button className="ghostButton" type="button" onClick={() => props.onStatus("complete")}>Mark complete</button> : null}{props.canEdit && meeting.status.toUpperCase() !== "CANCELLED" ? <button className="ghostButton" type="button" onClick={() => props.onStatus("cancel")}>Cancel meeting</button> : null}{props.canEdit && ["COMPLETED", "CANCELLED"].includes(meeting.status.toUpperCase()) ? <button className="ghostButton" type="button" onClick={() => props.onStatus("reopen")}>Reopen</button> : null}</div><div className="meetingDetailSections"><section><h3>Participants</h3>{meeting.participants.length ? <ul className="plainList">{meeting.participants.map((participant) => <li key={participant.id}><strong>{participant.name || participant.email}</strong><span>{statusLabel(participant.attendance_status)}</span></li>)}</ul> : <p>No participants added yet.</p>}{props.canEdit ? <form className="inlineForm" onSubmit={props.onParticipantSubmit}><select required value={props.participantUserId} onChange={(event) => props.onParticipantUserChange(event.target.value)}><option value="">Add an event member</option>{props.members.filter((member) => !meeting.participants.some((participant) => participant.user_id === member.user_id)).map((member) => <option key={member.user_id} value={member.user_id}>{member.user_name || member.user_email}</option>)}</select><select value={props.participantStatus} onChange={(event) => props.onParticipantStatusChange(event.target.value)}><option>INVITED</option><option>ACCEPTED</option><option>TENTATIVE</option><option>DECLINED</option></select><button className="ghostButton" type="submit">Add</button></form> : null}</section><section><h3>Agenda</h3>{meeting.agenda_items.length ? <ol className="plainList">{meeting.agenda_items.map((item: MeetingAgendaItem) => <li key={item.id}><strong>{item.title}</strong>{item.description ? <span>{item.description}</span> : null}</li>)}</ol> : <p>{meeting.agenda || "No agenda items yet."}</p>}{props.canEdit ? <form className="inlineForm" onSubmit={props.onAgendaSubmit}><input required value={props.agendaTitle} onChange={(event) => props.onAgendaTitleChange(event.target.value)} placeholder="Add agenda item" /><button className="ghostButton" type="submit">Add</button></form> : null}</section><section><h3>Notes and decisions</h3><form className="stack" onSubmit={props.onNotesSubmit}>{props.canEdit ? <><textarea value={props.notes} onChange={(event) => props.onNotesChange(event.target.value)} rows={4} placeholder="Record meeting notes" /><button className="ghostButton" type="submit">Save notes</button></> : <p>{meeting.notes || "No notes yet."}</p>}</form>{meeting.decisions.length ? <ul className="plainList">{meeting.decisions.map((decision: MeetingDecision) => <li key={decision.id}><strong>{decision.decision_text}</strong><span>{decision.recorder_name || "Event team"}</span></li>)}</ul> : null}{props.canEdit ? <form className="inlineForm" onSubmit={props.onDecisionSubmit}><input required value={props.decisionText} onChange={(event) => props.onDecisionTextChange(event.target.value)} placeholder="Record a decision" /><button className="ghostButton" type="submit">Add decision</button></form> : null}</section><section><h3>Follow-up tasks</h3>{meeting.follow_up_tasks.length ? <ul className="plainList">{meeting.follow_up_tasks.map((task) => <li key={task.id}><strong>{task.title}</strong><span>{statusLabel(task.status)}{task.due_date ? ` · due ${task.due_date}` : ""}</span></li>)}</ul> : <p>No follow-up tasks yet.</p>}{props.canEdit ? <form className="inlineForm" onSubmit={props.onTaskSubmit}><input required value={props.taskTitle} onChange={(event) => props.onTaskTitleChange(event.target.value)} placeholder="Add a follow-up task" /><input type="date" value={props.taskDueDate} onChange={(event) => props.onTaskDueDateChange(event.target.value)} /><button className="ghostButton" type="submit">Add task</button></form> : null}</section><section><h3>Documents</h3>{meeting.documents.length ? <ul className="plainList">{meeting.documents.map((document) => <li key={document.id}><strong>{document.original_filename || "Event document"}</strong><span>{document.category || "Planning"}</span></li>)}</ul> : <p>No documents linked. Use Documents to upload planning material for the event.</p>}</section></div></article>;
}
