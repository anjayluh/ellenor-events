"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../lib/api";
import { getAccessToken, subscribeToAuthChanges } from "../lib/session";
import type { BudgetResponse, Project, ProjectRole } from "../lib/types";
import { ProjectOnboardingForm } from "./ProjectOnboardingForm";
import { StateBlock } from "./StateBlock";

type Meeting = { id: string; type: string; title: string; agenda?: string | null; scheduled_time: string; status: string };
type Task = { id: string; title: string; status: string; due_date?: string | null };
type Vendor = { id: string; name: string; category: string; status: string; contact?: string | null };
type StaffDashboard = { active_projects: number; archived_projects: number; risk_alerts: Array<{ title: string; severity: string; message: string }>; project_health: Array<{ title: string; risk_level: string; pending_task_count: number; overdue_task_count: number; meeting_count: number; budget_variance: number }> };

const COORDINATOR_ROLES: ProjectRole[] = ["OWNER", "PARTNER", "COMMITTEE_CHAIR", "COMMITTEE_MEMBER"];
const BUDGET_EDITOR_ROLES: ProjectRole[] = ["OWNER", "PARTNER"];

function canCoordinate(role?: ProjectRole | null) {
  return Boolean(role && COORDINATOR_ROLES.includes(role));
}

function canEditBudget(role?: ProjectRole | null) {
  return Boolean(role && BUDGET_EDITOR_ROLES.includes(role));
}

function useFirstProject() {
  const [project, setProject] = useState<Project | null>(null);
  const [state, setState] = useState<"anonymous" | "loading" | "ready" | "empty" | "error">("loading");
  const [message, setMessage] = useState("");

  async function load() {
    const token = getAccessToken();
    if (!token) {
      setState("anonymous");
      setProject(null);
      return;
    }

    setState("loading");
    try {
      const projects = await apiGet<Project[]>("/projects", token);
      setProject(projects[0] ?? null);
      setState(projects[0] ? "ready" : "empty");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load your project membership.");
      setState("error");
    }
  }

  useEffect(() => {
    void load();
    return subscribeToAuthChanges(() => void load());
  }, []);

  return { project, state, message, reload: load };
}

function Guard({ state, message, onCreated }: { state: string; message?: string; onCreated?: () => void }) {
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
  if (state === "error") return <StateBlock title="Could not load data" message={message || "Please try again."} />;
  return null;
}

export function MeetingsClientPage() {
  const { project, state, message, reload } = useFirstProject();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [title, setTitle] = useState("");
  const [agenda, setAgenda] = useState("");
  const [meetingType, setMeetingType] = useState("committee");
  const [scheduledTime, setScheduledTime] = useState("");
  const [processing, setProcessing] = useState<string | null>(null);
  const [formMessage, setFormMessage] = useState("Create a meeting and let members RSVP.");
  const [touched, setTouched] = useState<Record<string, boolean>>({});

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

  const guard = <Guard state={state} message={message} onCreated={() => void reload()} />;
  if (state !== "ready") return guard;

  return (
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
              <span className="helperText">Optional, but useful for keeping cross-family meetings focused.</span>
            </label>
            <button className="primaryButton" disabled={!canSubmitMeeting || processing === "meeting-create"} type="submit">{processing === "meeting-create" ? "Creating..." : "Create meeting"}</button>
          </form>
        ) : <p>Your role can view and RSVP to meetings, but cannot create them.</p>}
        <p>{formMessage}</p>
      </article>

      <section className="stack">
        {meetings.length ? meetings.map((meeting) => (
          <article className="panel" key={meeting.id}>
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
            </div>
          </article>
        )) : <StateBlock title="No meetings yet" message={canCoordinate(project?.role) ? "Create the first planning touchpoint." : "Meetings created for your event will appear here."} />}
      </section>
    </section>
  );
}

export function BudgetClientPage() {
  const { project, state, message, reload } = useFirstProject();
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

  const guard = <Guard state={state} message={message} onCreated={() => void reload()} />;
  if (state !== "ready") return guard;
  if (!budget) return <StateBlock title="Budget unavailable" message="Your role may not have budget access for this event." />;

  return (
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
            <button className="primaryButton" disabled={!canSubmitBudget || isSubmitting} type="submit">{isSubmitting ? "Saving..." : "Save budget"}</button>
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
  );
}

export function CommitteeClientPage() {
  const { project, state, message, reload } = useFirstProject();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [formMessage, setFormMessage] = useState("Create and assign committee work.");
  const [isSubmitting, setIsSubmitting] = useState(false);

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

  const guard = <Guard state={state} message={message} onCreated={() => void reload()} />;
  if (state !== "ready") return guard;

  return (
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
        {tasks.length ? tasks.map((task) => <article className="panel" key={task.id}><p className="eyebrow">{task.status}</p><h2>{task.title}</h2><p>Due: {task.due_date ?? "Not set"}</p></article>) : <StateBlock title="No tasks yet" message={canCoordinate(project?.role) ? "Create the first committee task." : "Committee tasks will appear here once created."} />}
      </section>
    </section>
  );
}

export function VendorsClientPage() {
  const { project, state, message, reload } = useFirstProject();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [contact, setContact] = useState("");
  const [formMessage, setFormMessage] = useState("Create a shared vendor shortlist.");
  const [isSubmitting, setIsSubmitting] = useState(false);

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

  const guard = <Guard state={state} message={message} onCreated={() => void reload()} />;
  if (state !== "ready") return guard;

  return (
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
        {vendors.length ? vendors.map((vendor) => <article className="panel" key={vendor.id}><p className="eyebrow">{vendor.category}</p><h2>{vendor.name}</h2><p>Status: {vendor.status}</p><p>Contact: {vendor.contact ?? "Not set"}</p></article>) : <StateBlock title="No vendors yet" message={canCoordinate(project?.role) ? "Add the first vendor option." : "Vendor directory records will appear here once created."} />}
      </section>
    </section>
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
      .catch((error) => { setState(error && typeof error === "object" && "status" in error && error.status === 403 ? "denied" : "error"); });
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
