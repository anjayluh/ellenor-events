"use client";

import { FormEvent, useEffect, useState } from "react";
import { ApiError, apiDelete, apiGet, apiPatch, apiPost } from "../lib/api";
import { getAccessToken } from "../lib/session";
import { useActiveProject } from "../lib/useActiveProject";
import type { BudgetResponse, Project, ProjectRole } from "../lib/types";
import { ActiveEventSwitcher } from "./ActiveEventSwitcher";
import { ProjectOnboardingForm } from "./ProjectOnboardingForm";
import { StateBlock } from "./StateBlock";

type Meeting = { id: string; type: string; title: string; agenda?: string | null; scheduled_time: string; status: string };
type Task = { id: string; title: string; status: string; due_date?: string | null };
type Vendor = { id: string; name: string; category: string; status: string; contact?: string | null };
type Invite = { id: string; project_id: string; contact: string; role_assigned: ProjectRole; status: string; invite_link: string; delivery_channel: string; expires_at: string; sent_count: number; opened_count: number };
type StaffDashboard = { active_projects: number; archived_projects: number; risk_alerts: Array<{ title: string; severity: string; message: string }>; project_health: Array<{ title: string; risk_level: string; pending_task_count: number; overdue_task_count: number; meeting_count: number; budget_variance: number }> };

const COORDINATOR_ROLES: ProjectRole[] = ["OWNER", "PARTNER", "COMMITTEE_CHAIR", "COMMITTEE_MEMBER"];
const BUDGET_EDITOR_ROLES: ProjectRole[] = ["OWNER", "PARTNER"];
const PROJECT_ADMIN_ROLES: ProjectRole[] = ["OWNER", "PARTNER", "COMMITTEE_CHAIR"];
const VENDOR_STAGE_LABELS: Record<string, { label: string; description: string }> = {
  shortlisted: { label: "Considering", description: "Added as an option; no final decision yet." },
  quote_requested: { label: "Waiting for quote", description: "The team needs pricing or availability before deciding." },
  preferred: { label: "Preferred option", description: "This is the current leading choice." },
  booked: { label: "Booked", description: "Confirmed for the event." },
  rejected: { label: "Not selected", description: "Kept for history, but not moving forward." }
};

const TASK_STATUS_LABELS: Record<string, string> = {
  todo: "To do",
  in_progress: "In progress",
  done: "Done"
};

function toDateTimeLocal(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function vendorStage(status: string) {
  return VENDOR_STAGE_LABELS[status] ?? { label: status.replaceAll("_", " "), description: "Custom vendor stage." };
}

function canCoordinate(role?: ProjectRole | null) {
  return Boolean(role && COORDINATOR_ROLES.includes(role));
}

function canEditBudget(role?: ProjectRole | null) {
  return Boolean(role && BUDGET_EDITOR_ROLES.includes(role));
}

function canManageInvites(role?: ProjectRole | null) {
  return Boolean(role && PROJECT_ADMIN_ROLES.includes(role));
}

function Guard({
  state,
  message,
  onCreated,
  projects = [],
  onSelect
}: {
  state: string;
  message?: string;
  onCreated?: () => void;
  projects?: Project[];
  onSelect?: (projectId: string) => void;
}) {
  if (state === "anonymous") return <StateBlock title="Login required" message="Sign in before viewing private event data." />;
  if (state === "loading") return <StateBlock title="Loading" message="Fetching live data from the backend." />;
  if (state === "empty") {
    return (
      <section className="grid twoColumns">
        <StateBlock title="Create your first event" message="You are signed in, but you are not a member of any event yet. Start one now or accept an invite." />
        <ProjectOnboardingForm onCreated={onCreated} />
      </section>
    );
  }
  if (state === "selection_required") {
    return (
      <section className="panel actionPanel eventSelectionPanel">
        <p className="eyebrow">Choose Event</p>
        <h2>This page needs an event workspace.</h2>
        <p>{message || "Select the event whose meetings, budget, committee, vendors, or invites you want to manage."}</p>
        <div className="stack">
          {projects.map((project) => (
            <button className="ghostButton eventChoiceButton" key={project.id} type="button" onClick={() => onSelect?.(project.id)}>
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

export function MeetingsClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [title, setTitle] = useState("");
  const [agenda, setAgenda] = useState("");
  const [meetingType, setMeetingType] = useState("committee");
  const [scheduledTime, setScheduledTime] = useState("");
  const [processing, setProcessing] = useState<string | null>(null);
  const [formMessage, setFormMessage] = useState("Create a meeting and let members RSVP.");
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [editingMeetingId, setEditingMeetingId] = useState<string | null>(null);
  const [editMeeting, setEditMeeting] = useState({ title: "", type: "", agenda: "", scheduledTime: "" });

  async function loadMeetings(activeProject: Project) {
    setMeetings(await apiGet<Meeting[]>(`/projects/${activeProject.id}/meetings`));
  }

  useEffect(() => {
    if (!project) return;
    void loadMeetings(project).catch(() => setMeetings([]));
  }, [project]);

  const titleError = title && title.trim().length < 3 ? "Meeting title must be at least 3 characters." : "";
  const timeError = scheduledTime && new Date(scheduledTime).getTime() <= Date.now() ? "Meeting time must be in the future." : "";
  const canSubmitMeeting = canCoordinate(project?.role) && title.trim().length >= 3 && Boolean(scheduledTime) && !titleError && !timeError;

  async function createMeeting(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmitMeeting || processing) return;

    setProcessing("meeting-create");
    setFormMessage("Creating meeting...");
    try {
      await apiPost<Meeting, { type: string; title: string; agenda?: string | null; scheduled_time: string }>(`/projects/${project.id}/meetings`, {
        type: meetingType,
        title: title.trim(),
        agenda: agenda.trim() || null,
        scheduled_time: new Date(scheduledTime).toISOString()
      });
      setTitle("");
      setAgenda("");
      setScheduledTime("");
      setFormMessage("Meeting created.");
      await loadMeetings(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not create meeting.");
    } finally {
      setProcessing(null);
    }
  }

  async function rsvp(meetingId: string, status: string) {
    setProcessing(`${meetingId}-${status}`);
    try {
      await apiPost(`/projects/${project?.id}/meetings/${meetingId}/rsvp`, { status });
    } finally {
      setProcessing(null);
    }
  }

  function startMeetingEdit(meeting: Meeting) {
    setEditingMeetingId(meeting.id);
    setEditMeeting({
      title: meeting.title,
      type: meeting.type,
      agenda: meeting.agenda ?? "",
      scheduledTime: toDateTimeLocal(meeting.scheduled_time)
    });
  }

  async function updateMeeting(meetingId: string) {
    if (!project || processing) return;
    setProcessing(`meeting-update-${meetingId}`);
    setFormMessage("Saving meeting changes...");
    try {
      await apiPatch<Meeting, { title: string; type: string; agenda?: string | null; scheduled_time: string }>(`/projects/${project.id}/meetings/${meetingId}`, {
        title: editMeeting.title.trim(),
        type: editMeeting.type.trim(),
        agenda: editMeeting.agenda.trim() || null,
        scheduled_time: new Date(editMeeting.scheduledTime).toISOString()
      });
      setEditingMeetingId(null);
      setFormMessage("Meeting updated.");
      await loadMeetings(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not update meeting.");
    } finally {
      setProcessing(null);
    }
  }

  async function deleteMeeting(meetingId: string) {
    if (!project || processing || !window.confirm("Delete this meeting from the selected event?")) return;
    setProcessing(`meeting-delete-${meetingId}`);
    setFormMessage("Deleting meeting...");
    try {
      await apiDelete<{ status: string }>(`/projects/${project.id}/meetings/${meetingId}`);
      setFormMessage("Meeting deleted.");
      await loadMeetings(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not delete meeting.");
    } finally {
      setProcessing(null);
    }
  }

  const guard = <Guard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;
  if (state !== "ready") return guard;

  return (
    <>
    <ActiveEventSwitcher projects={projects} activeProjectId={project?.id} onChange={selectProject} />
    <section className="grid twoColumns">
      <article className="panel actionPanel">
        <p className="eyebrow">Meetings</p>
        <h2>Plan the next committee touchpoint</h2>
        {canCoordinate(project?.role) ? (
          <form className="stack" onSubmit={createMeeting}>
            <label className="formField">
              Meeting title
              <input value={title} onBlur={() => setTouched((current) => ({ ...current, title: true }))} onChange={(event) => setTitle(event.target.value)} placeholder="Decor review with families" aria-invalid={Boolean(titleError)} />
              <span className="helperText">At least 3 characters. Keep it clear for aunties, uncles, vendors, and committee members.</span>
              {touched.title && titleError ? <span className="errorText">{titleError}</span> : null}
            </label>
            <label className="formField">
              Meeting type
              <input value={meetingType} onChange={(event) => setMeetingType(event.target.value)} placeholder="committee" />
              <span className="helperText">Examples: committee, family, vendor, budget.</span>
            </label>
            <label className="formField">
              Scheduled time
              <input value={scheduledTime} onBlur={() => setTouched((current) => ({ ...current, scheduledTime: true }))} onChange={(event) => setScheduledTime(event.target.value)} type="datetime-local" aria-invalid={Boolean(timeError)} />
              <span className="helperText">Required. Use a future date and time.</span>
              {touched.scheduledTime && timeError ? <span className="errorText">{timeError}</span> : null}
            </label>
            <label className="formField">
              Agenda
              <input value={agenda} onChange={(event) => setAgenda(event.target.value)} placeholder="Confirm decor, seating, and contribution updates" />
              <span className="helperText">Optional, but useful for keeping meetings focused.</span>
            </label>
            <button className="primaryButton" disabled={!canSubmitMeeting || processing === "meeting-create"} type="submit">{processing === "meeting-create" ? "Creating..." : "Create meeting"}</button>
          </form>
        ) : <p>Your role can view and RSVP to meetings, but cannot create them.</p>}
        <p>{formMessage}</p>
      </article>

      <section className="stack">
        {meetings.length ? meetings.map((meeting) => (
          <article className="panel" key={meeting.id}>
            {editingMeetingId === meeting.id ? (
              <div className="stack">
                <p className="eyebrow">Edit meeting</p>
                <label className="formField">Title<input value={editMeeting.title} onChange={(event) => setEditMeeting((current) => ({ ...current, title: event.target.value }))} /></label>
                <label className="formField">Type<input value={editMeeting.type} onChange={(event) => setEditMeeting((current) => ({ ...current, type: event.target.value }))} /></label>
                <label className="formField">Scheduled time<input type="datetime-local" value={editMeeting.scheduledTime} onChange={(event) => setEditMeeting((current) => ({ ...current, scheduledTime: event.target.value }))} /></label>
                <label className="formField">Agenda<input value={editMeeting.agenda} onChange={(event) => setEditMeeting((current) => ({ ...current, agenda: event.target.value }))} /></label>
                <div className="buttonRow">
                  <button className="primaryButton" disabled={!editMeeting.title.trim() || !editMeeting.type.trim() || !editMeeting.scheduledTime || Boolean(processing)} type="button" onClick={() => void updateMeeting(meeting.id)}>{processing === `meeting-update-${meeting.id}` ? "Saving..." : "Save changes"}</button>
                  <button className="ghostButton" disabled={Boolean(processing)} type="button" onClick={() => setEditingMeetingId(null)}>Cancel</button>
                </div>
              </div>
            ) : (
              <>
                <p className="eyebrow">{meeting.type}</p>
                <h2>{meeting.title}</h2>
                <p>{new Date(meeting.scheduled_time).toLocaleString()}</p>
                <p>{meeting.agenda ?? "No agenda yet."}</p>
                <div className="buttonRow">
                  {["accepted", "tentative", "declined"].map((status) => (
                    <button className={status === "accepted" ? "primaryButton" : "ghostButton"} disabled={Boolean(processing)} key={status} type="button" onClick={() => void rsvp(meeting.id, status)}>
                      {processing === `${meeting.id}-${status}` ? "Saving..." : status}
                    </button>
                  ))}
                  {canCoordinate(project?.role) ? <button className="ghostButton" disabled={Boolean(processing)} type="button" onClick={() => startMeetingEdit(meeting)}>Edit</button> : null}
                  {canManageInvites(project?.role) ? <button className="ghostButton danger" disabled={Boolean(processing)} type="button" onClick={() => void deleteMeeting(meeting.id)}>{processing === `meeting-delete-${meeting.id}` ? "Deleting..." : "Delete"}</button> : null}
                </div>
              </>
            )}
          </article>
        )) : <StateBlock title="No meetings yet" message={canCoordinate(project?.role) ? "Create the first planning touchpoint." : "Meetings created for your event will appear here."} />}
      </section>
    </section>
    </>
  );
}

export function BudgetClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [budget, setBudget] = useState<BudgetResponse | null>(null);
  const [total, setTotal] = useState("");
  const [spent, setSpent] = useState("");
  const [formMessage, setFormMessage] = useState("Owners and partners can update budget totals.");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadBudget(activeProject: Project) {
    const nextBudget = await apiGet<BudgetResponse>(`/projects/${activeProject.id}/budget`);
    setBudget(nextBudget);
    setTotal(nextBudget.total == null ? "" : String(nextBudget.total));
    setSpent(nextBudget.spent == null ? "" : String(nextBudget.spent));
  }

  useEffect(() => {
    if (!project) return;
    void loadBudget(project).catch(() => setBudget(null));
  }, [project]);

  const totalValue = Number(total);
  const spentValue = Number(spent);
  const totalError = total && (Number.isNaN(totalValue) || totalValue < 0) ? "Total must be zero or more." : "";
  const spentError = spent && (Number.isNaN(spentValue) || spentValue < 0) ? "Spent amount must be zero or more." : "";
  const overspendError = total && spent && spentValue > totalValue ? "Spent cannot be greater than total." : "";
  const budgetChanged = budget ? totalValue !== Number(budget.total ?? 0) || spentValue !== Number(budget.spent ?? 0) : false;
  const canSubmitBudget = canEditBudget(project?.role) && Boolean(total) && Boolean(spent) && budgetChanged && !totalError && !spentError && !overspendError;

  async function updateBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmitBudget || isSubmitting) return;

    setIsSubmitting(true);
    setFormMessage("Saving budget...");
    try {
      await apiPatch<BudgetResponse, { total: number; spent: number }>(`/projects/${project.id}/budget`, { total: totalValue, spent: spentValue });
      setFormMessage("Budget updated.");
      await loadBudget(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not update budget.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function resetBudget() {
    if (!project || isSubmitting || !window.confirm("Reset this event budget to zero? Existing budget totals will be cleared.")) return;
    setIsSubmitting(true);
    setFormMessage("Resetting budget...");
    try {
      await apiPatch<BudgetResponse, { total: number; spent: number }>(`/projects/${project.id}/budget`, { total: 0, spent: 0 });
      setFormMessage("Budget reset to zero.");
      await loadBudget(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not reset budget.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const guard = <Guard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;
  if (state !== "ready") return guard;
  if (!budget) return <StateBlock title="Budget unavailable" message="Your role may not have budget access for this event." />;

  return (
    <>
    <ActiveEventSwitcher projects={projects} activeProjectId={project?.id} onChange={selectProject} />
    <section className="grid twoColumns">
      <article className="panel">
        <p className="eyebrow">{budget.visibility.replaceAll("_", " ")}</p>
        <h2>Budget View</h2>
        <p>Total: {budget.total == null ? "Hidden" : `UGX ${budget.total.toLocaleString()}`}</p>
        <p>Spent: {budget.spent == null ? "Hidden" : `UGX ${budget.spent.toLocaleString()}`}</p>
        <p>Remaining: {budget.remaining == null ? "Hidden" : `UGX ${budget.remaining.toLocaleString()}`}</p>
      </article>
      <article className="panel actionPanel">
        <h2>Update Budget</h2>
        {canEditBudget(project?.role) ? (
          <form className="stack" onSubmit={updateBudget}>
            <label className="formField">
              Total budget
              <input inputMode="numeric" value={total} onChange={(event) => setTotal(event.target.value)} placeholder="42000000" aria-invalid={Boolean(totalError)} />
              <span className="helperText">Required. Use UGX numbers only; zero or more.</span>
              {totalError ? <span className="errorText">{totalError}</span> : null}
            </label>
            <label className="formField">
              Spent so far
              <input inputMode="numeric" value={spent} onChange={(event) => setSpent(event.target.value)} placeholder="7500000" aria-invalid={Boolean(spentError || overspendError)} />
              <span className="helperText">Required. Must be zero or more and cannot exceed the total.</span>
              {spentError || overspendError ? <span className="errorText">{spentError || overspendError}</span> : null}
            </label>
            <div className="buttonRow">
              <button className="primaryButton" disabled={!canSubmitBudget || isSubmitting} type="submit">{isSubmitting ? "Saving..." : "Save budget"}</button>
              <button className="ghostButton danger" disabled={isSubmitting || (Number(budget.total ?? 0) === 0 && Number(budget.spent ?? 0) === 0)} type="button" onClick={() => void resetBudget()}>Reset budget</button>
            </div>
          </form>
        ) : <p>Your role can view the shaped budget summary allowed by the backend, but cannot edit totals.</p>}
        <p>{formMessage}</p>
      </article>
      <article className="panel">
        <h2>Contribution Progress</h2>
        <p>Paid: {budget.contribution_progress == null ? "Hidden" : `UGX ${budget.contribution_progress.toLocaleString()}`}</p>
        <p>Pledged: {budget.pledged_total == null ? "Hidden" : `UGX ${budget.pledged_total.toLocaleString()}`}</p>
      </article>
    </section>
    </>
  );
}

export function CommitteeClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [formMessage, setFormMessage] = useState("Create and assign committee work.");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [taskProcessing, setTaskProcessing] = useState<string | null>(null);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [editTask, setEditTask] = useState({ title: "", status: "todo", dueDate: "" });

  async function loadTasks(activeProject: Project) {
    setTasks(await apiGet<Task[]>(`/projects/${activeProject.id}/tasks`));
  }

  useEffect(() => {
    if (!project) return;
    void loadTasks(project).catch(() => setTasks([]));
  }, [project]);

  const titleError = title && title.trim().length < 3 ? "Task title must be at least 3 characters." : "";
  const canSubmitTask = canCoordinate(project?.role) && title.trim().length >= 3 && !titleError;

  async function createTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmitTask || isSubmitting) return;

    setIsSubmitting(true);
    setFormMessage("Creating task...");
    try {
      await apiPost<Task, { title: string; status: string; due_date?: string | null }>(`/projects/${project.id}/tasks`, {
        title: title.trim(),
        status: "todo",
        due_date: dueDate || null
      });
      setTitle("");
      setDueDate("");
      setFormMessage("Task created.");
      await loadTasks(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not create task.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function startTaskEdit(task: Task) {
    setEditingTaskId(task.id);
    setEditTask({ title: task.title, status: task.status, dueDate: task.due_date ?? "" });
  }

  async function updateTask(taskId: string) {
    if (!project || taskProcessing) return;
    setTaskProcessing(`task-update-${taskId}`);
    setFormMessage("Saving task changes...");
    try {
      await apiPatch<Task, { title: string; status: string; due_date?: string | null }>(`/projects/${project.id}/tasks/${taskId}`, {
        title: editTask.title.trim(),
        status: editTask.status,
        due_date: editTask.dueDate || null
      });
      setEditingTaskId(null);
      setFormMessage("Task updated.");
      await loadTasks(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not update task.");
    } finally {
      setTaskProcessing(null);
    }
  }

  async function deleteTask(taskId: string) {
    if (!project || taskProcessing || !window.confirm("Delete this committee task from the selected event?")) return;
    setTaskProcessing(`task-delete-${taskId}`);
    setFormMessage("Deleting task...");
    try {
      await apiDelete<{ status: string }>(`/projects/${project.id}/tasks/${taskId}`);
      setFormMessage("Task deleted.");
      await loadTasks(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not delete task.");
    } finally {
      setTaskProcessing(null);
    }
  }

  const guard = <Guard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;
  if (state !== "ready") return guard;

  return (
    <>
    <ActiveEventSwitcher projects={projects} activeProjectId={project?.id} onChange={selectProject} />
    <section className="grid twoColumns">
      <article className="panel actionPanel">
        <p className="eyebrow">Committee</p>
        <h2>Add committee task</h2>
        {canCoordinate(project?.role) ? (
          <form className="stack" onSubmit={createTask}>
            <label className="formField">
              Task title
              <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Confirm family transport" aria-invalid={Boolean(titleError)} />
              <span className="helperText">At least 3 characters. Make it specific enough for someone to act.</span>
              {titleError ? <span className="errorText">{titleError}</span> : null}
            </label>
            <label className="formField">
              Due date
              <input value={dueDate} onChange={(event) => setDueDate(event.target.value)} type="date" />
              <span className="helperText">Optional. Use it for time-sensitive wedding and introduction tasks.</span>
            </label>
            <button className="primaryButton" disabled={!canSubmitTask || isSubmitting} type="submit">{isSubmitting ? "Creating..." : "Create task"}</button>
          </form>
        ) : <p>Your role can view committee progress but cannot create tasks.</p>}
        <p>{formMessage}</p>
      </article>
      <section className="grid twoColumns">
        {tasks.length ? tasks.map((task) => (
          <article className="panel" key={task.id}>
            {editingTaskId === task.id ? (
              <div className="stack">
                <p className="eyebrow">Edit task</p>
                <label className="formField">Task title<input value={editTask.title} onChange={(event) => setEditTask((current) => ({ ...current, title: event.target.value }))} /></label>
                <label className="formField">Status<select value={editTask.status} onChange={(event) => setEditTask((current) => ({ ...current, status: event.target.value }))}><option value="todo">To do</option><option value="in_progress">In progress</option><option value="done">Done</option></select></label>
                <label className="formField">Due date<input type="date" value={editTask.dueDate} onChange={(event) => setEditTask((current) => ({ ...current, dueDate: event.target.value }))} /></label>
                <div className="buttonRow">
                  <button className="primaryButton" disabled={!editTask.title.trim() || Boolean(taskProcessing)} type="button" onClick={() => void updateTask(task.id)}>{taskProcessing === `task-update-${task.id}` ? "Saving..." : "Save changes"}</button>
                  <button className="ghostButton" disabled={Boolean(taskProcessing)} type="button" onClick={() => setEditingTaskId(null)}>Cancel</button>
                </div>
              </div>
            ) : (
              <>
                <p className="eyebrow">{TASK_STATUS_LABELS[task.status] ?? task.status.replaceAll("_", " ")}</p>
                <h2>{task.title}</h2>
                <p>Due: {task.due_date ?? "Not set"}</p>
                {canCoordinate(project?.role) ? (
                  <div className="buttonRow">
                    <button className="ghostButton" disabled={Boolean(taskProcessing)} type="button" onClick={() => startTaskEdit(task)}>Edit</button>
                    <button className="ghostButton danger" disabled={Boolean(taskProcessing)} type="button" onClick={() => void deleteTask(task.id)}>{taskProcessing === `task-delete-${task.id}` ? "Deleting..." : "Delete"}</button>
                  </div>
                ) : null}
              </>
            )}
          </article>
        )) : <StateBlock title="No tasks yet" message={canCoordinate(project?.role) ? "Create the first committee task." : "Committee tasks will appear here once created."} />}
      </section>
    </section>
    </>
  );
}

export function VendorsClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [contact, setContact] = useState("");
  const [formMessage, setFormMessage] = useState("Create a shared vendor shortlist.");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [vendorProcessing, setVendorProcessing] = useState<string | null>(null);
  const [editingVendorId, setEditingVendorId] = useState<string | null>(null);
  const [editVendor, setEditVendor] = useState({ name: "", category: "", contact: "", status: "shortlisted" });

  async function loadVendors(activeProject: Project) {
    setVendors(await apiGet<Vendor[]>(`/projects/${activeProject.id}/vendors`));
  }

  useEffect(() => {
    if (!project) return;
    void loadVendors(project).catch(() => setVendors([]));
  }, [project]);

  const nameError = name && name.trim().length < 2 ? "Vendor name must be at least 2 characters." : "";
  const categoryError = category && category.trim().length < 2 ? "Category must be at least 2 characters." : "";
  const canSubmitVendor = canCoordinate(project?.role) && name.trim().length >= 2 && category.trim().length >= 2 && !nameError && !categoryError;

  async function createVendor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmitVendor || isSubmitting) return;

    setIsSubmitting(true);
    setFormMessage("Creating vendor...");
    try {
      await apiPost<Vendor, { name: string; category: string; contact?: string | null; status: string }>(`/projects/${project.id}/vendors`, {
        name: name.trim(),
        category: category.trim(),
        contact: contact.trim() || null,
        status: "shortlisted"
      });
      setName("");
      setCategory("");
      setContact("");
      setFormMessage("Vendor added.");
      await loadVendors(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not create vendor.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function startVendorEdit(vendor: Vendor) {
    setEditingVendorId(vendor.id);
    setEditVendor({
      name: vendor.name,
      category: vendor.category,
      contact: vendor.contact ?? "",
      status: vendor.status
    });
  }

  async function updateVendor(vendorId: string) {
    if (!project || vendorProcessing) return;
    setVendorProcessing(`vendor-update-${vendorId}`);
    setFormMessage("Saving vendor changes...");
    try {
      await apiPatch<Vendor, { name: string; category: string; contact?: string | null; status: string }>(`/projects/${project.id}/vendors/${vendorId}`, {
        name: editVendor.name.trim(),
        category: editVendor.category.trim(),
        contact: editVendor.contact.trim() || null,
        status: editVendor.status
      });
      setEditingVendorId(null);
      setFormMessage("Vendor updated.");
      await loadVendors(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not update vendor.");
    } finally {
      setVendorProcessing(null);
    }
  }

  async function deleteVendor(vendorId: string) {
    if (!project || vendorProcessing || !window.confirm("Delete this vendor from the selected event?")) return;
    setVendorProcessing(`vendor-delete-${vendorId}`);
    setFormMessage("Deleting vendor...");
    try {
      await apiDelete<{ status: string }>(`/projects/${project.id}/vendors/${vendorId}`);
      setFormMessage("Vendor deleted.");
      await loadVendors(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not delete vendor.");
    } finally {
      setVendorProcessing(null);
    }
  }

  const guard = <Guard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;
  if (state !== "ready") return guard;

  return (
    <>
    <ActiveEventSwitcher projects={projects} activeProjectId={project?.id} onChange={selectProject} />
    <section className="grid twoColumns">
      <article className="panel actionPanel">
        <p className="eyebrow">Vendors</p>
        <h2>Add vendor option</h2>
        {canCoordinate(project?.role) ? (
          <form className="stack" onSubmit={createVendor}>
            <label className="formField">
              Vendor name
              <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Pearl Gardens Catering" aria-invalid={Boolean(nameError)} />
              <span className="helperText">At least 2 characters.</span>
              {nameError ? <span className="errorText">{nameError}</span> : null}
            </label>
            <label className="formField">
              Category
              <input value={category} onChange={(event) => setCategory(event.target.value)} placeholder="catering, decor, photography" aria-invalid={Boolean(categoryError)} />
              <span className="helperText">At least 2 characters. Use simple categories families understand.</span>
              {categoryError ? <span className="errorText">{categoryError}</span> : null}
            </label>
            <label className="formField">
              Contact
              <input value={contact} onChange={(event) => setContact(event.target.value)} placeholder="+256..." />
              <span className="helperText">Optional phone, email, or link.</span>
            </label>
            <button className="primaryButton" disabled={!canSubmitVendor || isSubmitting} type="submit">{isSubmitting ? "Adding..." : "Add vendor"}</button>
          </form>
        ) : <p>Your role can view vendor options but cannot add vendors.</p>}
        <p>{formMessage}</p>
      </article>
      <section className="grid twoColumns">
        {vendors.length ? vendors.map((vendor) => {
          const stage = vendorStage(vendor.status);
          return (
            <article className="panel" key={vendor.id}>
              {editingVendorId === vendor.id ? (
                <div className="stack">
                  <p className="eyebrow">Edit vendor</p>
                  <label className="formField">Vendor name<input value={editVendor.name} onChange={(event) => setEditVendor((current) => ({ ...current, name: event.target.value }))} /></label>
                  <label className="formField">Category<input value={editVendor.category} onChange={(event) => setEditVendor((current) => ({ ...current, category: event.target.value }))} /></label>
                  <label className="formField">Contact<input value={editVendor.contact} onChange={(event) => setEditVendor((current) => ({ ...current, contact: event.target.value }))} /></label>
                  <label className="formField">Decision stage<select value={editVendor.status} onChange={(event) => setEditVendor((current) => ({ ...current, status: event.target.value }))}><option value="shortlisted">Considering</option><option value="quote_requested">Waiting for quote</option><option value="preferred">Preferred option</option><option value="booked">Booked</option><option value="rejected">Not selected</option></select></label>
                  <div className="buttonRow">
                    <button className="primaryButton" disabled={!editVendor.name.trim() || !editVendor.category.trim() || Boolean(vendorProcessing)} type="button" onClick={() => void updateVendor(vendor.id)}>{vendorProcessing === `vendor-update-${vendor.id}` ? "Saving..." : "Save changes"}</button>
                    <button className="ghostButton" disabled={Boolean(vendorProcessing)} type="button" onClick={() => setEditingVendorId(null)}>Cancel</button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="eyebrow">{vendor.category}</p>
                  <h2>{vendor.name}</h2>
                  <p><strong>Decision stage:</strong> {stage.label}</p>
                  <p className="helperText">{stage.description}</p>
                  <p>Contact: {vendor.contact ?? "Not set"}</p>
                  {canCoordinate(project?.role) ? (
                    <div className="buttonRow">
                      <button className="ghostButton" disabled={Boolean(vendorProcessing)} type="button" onClick={() => startVendorEdit(vendor)}>Edit</button>
                      <button className="ghostButton danger" disabled={Boolean(vendorProcessing)} type="button" onClick={() => void deleteVendor(vendor.id)}>{vendorProcessing === `vendor-delete-${vendor.id}` ? "Deleting..." : "Delete"}</button>
                    </div>
                  ) : null}
                </>
              )}
            </article>
          );
        }) : <StateBlock title="No vendors yet" message={canCoordinate(project?.role) ? "Add the first vendor option." : "Vendor directory records will appear here once created."} />}
      </section>
    </section>
    </>
  );
}

export function InvitesClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [invites, setInvites] = useState<Invite[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<ProjectRole>("COMMITTEE_MEMBER");
  const [formMessage, setFormMessage] = useState("Invite collaborators by email to the selected event.");
  const [processing, setProcessing] = useState<string | null>(null);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  async function loadInvites(activeProject: Project) {
    setInvites(await apiGet<Invite[]>(`/invites/projects/${activeProject.id}`));
  }

  useEffect(() => {
    if (!project || !canManageInvites(project.role)) {
      setInvites([]);
      return;
    }
    void loadInvites(project).catch(() => setInvites([]));
  }, [project]);

  const emailError = email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? "Enter a valid email address." : "";
  const canSubmitInvite = Boolean(project && canManageInvites(project.role) && email && !emailError);

  async function createInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmitInvite || processing) return;

    setProcessing("invite-create");
    setFormMessage("Preparing email invite...");
    try {
      await apiPost<Invite, { project_id: string; contact: string; role_assigned: ProjectRole; delivery_channel: "email" }>("/invites", {
        project_id: project.id,
        contact: email.trim().toLowerCase(),
        role_assigned: role,
        delivery_channel: "email"
      });
      setEmail("");
      setFormMessage("Email invite prepared. Share the invite link if provider delivery is not enabled yet.");
      await loadInvites(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "Could not create invite.");
    } finally {
      setProcessing(null);
    }
  }

  async function runInviteAction(inviteId: string, action: "resend" | "cancel") {
    if (!project || processing) return;
    setProcessing(`${action}-${inviteId}`);
    try {
      await apiPost<Invite, Record<string, never>>(`/invites/${inviteId}/${action}`, {});
      setFormMessage(action === "resend" ? "Invite resent." : "Invite cancelled.");
      await loadInvites(project);
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : `Could not ${action} invite.`);
    } finally {
      setProcessing(null);
    }
  }

  const guard = <Guard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;
  if (state !== "ready") return guard;

  return (
    <>
      <ActiveEventSwitcher projects={projects} activeProjectId={project?.id} onChange={selectProject} />
      <section className="grid twoColumns">
        <article className="panel actionPanel">
          <p className="eyebrow">Email Invites</p>
          <h2>Add people to this event</h2>
          {canManageInvites(project?.role) ? (
            <form className="stack" onSubmit={createInvite}>
              <label className="formField">
                Recipient email
                <input value={email} onBlur={() => setTouched((current) => ({ ...current, email: true }))} onChange={(event) => setEmail(event.target.value)} placeholder="committee.member@example.com" type="email" aria-invalid={Boolean(emailError)} />
                <span className="helperText">Required. The invite is scoped only to {project?.title}.</span>
                {touched.email && emailError ? <span className="errorText">{emailError}</span> : null}
              </label>
              <label className="formField">
                Event role
                <select value={role} onChange={(event) => setRole(event.target.value as ProjectRole)}>
                  <option value="PARTNER">Partner</option>
                  <option value="COMMITTEE_CHAIR">Committee chair</option>
                  <option value="COMMITTEE_MEMBER">Committee member</option>
                  <option value="FAMILY_VIEWER">Family viewer</option>
                  <option value="GUEST_VIEWER">Guest viewer</option>
                </select>
                <span className="helperText">Roles control budget visibility, meetings, committee work, and vendor permissions.</span>
              </label>
              <button className="primaryButton" disabled={!canSubmitInvite || processing === "invite-create"} type="submit">{processing === "invite-create" ? "Preparing..." : "Send email invite"}</button>
            </form>
          ) : <p>Your role can participate in this event, but cannot invite members.</p>}
          <p>{formMessage}</p>
        </article>

        <section className="stack">
          {canManageInvites(project?.role) && invites.length ? invites.map((invite) => (
            <article className="panel" key={invite.id}>
              <p className="eyebrow">{invite.status} · {invite.delivery_channel}</p>
              <h2>{invite.contact}</h2>
              <p>Role: {invite.role_assigned.replaceAll("_", " ")}</p>
              <p>Sent {invite.sent_count} time(s), opened {invite.opened_count} time(s).</p>
              <p className="helperText">Pending invites can be cancelled. Accepted invites become event memberships and should be managed from member roles.</p>
              <p className="tokenNote">{invite.invite_link}</p>
              <div className="buttonRow">
                <button className="ghostButton" disabled={invite.status === "accepted" || Boolean(processing)} type="button" onClick={() => void runInviteAction(invite.id, "resend")}>
                  {processing === `resend-${invite.id}` ? "Resending..." : "Resend"}
                </button>
                <button className="ghostButton danger" disabled={invite.status === "accepted" || invite.status === "cancelled" || Boolean(processing)} type="button" onClick={() => void runInviteAction(invite.id, "cancel")}>
                  {processing === `cancel-${invite.id}` ? "Cancelling..." : "Cancel invite"}
                </button>
              </div>
            </article>
          )) : <StateBlock title="No invites yet" message={canManageInvites(project?.role) ? "Invite a partner, committee chair, family viewer, guest, or vendor contact by email." : "Invite tracking is available to owners, partners, and committee chairs."} />}
        </section>
      </section>
    </>
  );
}

export function StaffClientPage() {
  const [state, setState] = useState<"anonymous" | "loading" | "ready" | "denied" | "error">("loading");
  const [dashboard, setDashboard] = useState<StaffDashboard | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) { setState("anonymous"); return; }
    void apiGet<StaffDashboard>("/staff/dashboard", token)
      .then((data) => { setDashboard(data); setState("ready"); })
      .catch((error) => {
        if (error instanceof ApiError && error.status === 401) {
          setState("anonymous");
          return;
        }
        setState(error && typeof error === "object" && "status" in error && error.status === 403 ? "denied" : "error");
      });
  }, []);

  if (state === "anonymous") return <StateBlock title="Staff login required" message="Staff tools are internal-only and are not shown in public navigation." />;
  if (state === "loading") return <StateBlock title="Loading staff dashboard" message="Checking staff authorization." />;
  if (state === "denied") return <StateBlock title="Staff access required" message="Your account is not authorized for the staff portal." />;
  if (state === "error" || !dashboard) return <StateBlock title="Could not load staff dashboard" message="Please try again or contact an administrator." />;

  return (
    <>
      <section className="grid threeColumns">
        <article className="metric"><span>Active projects</span><strong>{dashboard.active_projects}</strong></article>
        <article className="metric"><span>Archived projects</span><strong>{dashboard.archived_projects}</strong></article>
        <article className="metric"><span>Risk alerts</span><strong>{dashboard.risk_alerts.length}</strong></article>
      </section>
      <section className="grid twoColumns">
        <article className="panel"><h2>Risk Alerts</h2><div className="stack">{dashboard.risk_alerts.map((alert) => <div className="eventCard" key={`${alert.title}-${alert.message}`}><p className="eyebrow">{alert.severity}</p><h3>{alert.title}</h3><p>{alert.message}</p></div>)}</div></article>
        <article className="panel"><h2>Project Health</h2><div className="stack">{dashboard.project_health.map((project) => <div className="eventCard" key={project.title}><p className="eyebrow">{project.risk_level} risk</p><h3>{project.title}</h3><p>{project.pending_task_count} pending, {project.overdue_task_count} overdue.</p><p>{project.meeting_count} meetings, budget variance {(project.budget_variance * 100).toFixed(0)}%.</p></div>)}</div></article>
      </section>
    </>
  );
}
