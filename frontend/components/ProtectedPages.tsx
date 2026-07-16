"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
import { getAccessToken, subscribeToAuthChanges } from "../lib/session";
import type { BudgetResponse, Project } from "../lib/types";
import { StateBlock } from "./StateBlock";

type Meeting = { id: string; type: string; title: string; agenda?: string | null; scheduled_time: string; status: string };
type Task = { id: string; title: string; status: string; due_date?: string | null };
type Vendor = { id: string; name: string; category: string; status: string; contact?: string | null };
type StaffDashboard = { active_projects: number; archived_projects: number; risk_alerts: Array<{ title: string; severity: string; message: string }>; project_health: Array<{ title: string; risk_level: string; pending_task_count: number; overdue_task_count: number; meeting_count: number; budget_variance: number }> };

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

  return { project, state, message };
}

function Guard({ state, message }: { state: string; message?: string }) {
  if (state === "anonymous") return <StateBlock title="Login required" message="Sign in before viewing private event data." />;
  if (state === "loading") return <StateBlock title="Loading" message="Fetching live data from the backend." />;
  if (state === "empty") return <StateBlock title="No event membership" message="Ask an owner or committee chair to add you to an event." />;
  if (state === "error") return <StateBlock title="Could not load data" message={message || "Please try again."} />;
  return null;
}

export function MeetingsClientPage() {
  const { project, state, message } = useFirstProject();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [processing, setProcessing] = useState<string | null>(null);

  useEffect(() => {
    if (!project) return;
    void apiGet<Meeting[]>(`/projects/${project.id}/meetings`).then(setMeetings).catch(() => setMeetings([]));
  }, [project]);

  async function rsvp(meetingId: string, status: string) {
    setProcessing(`${meetingId}-${status}`);
    try {
      await apiPost(`/projects/${project?.id}/meetings/${meetingId}/rsvp`, { status });
    } finally {
      setProcessing(null);
    }
  }

  const guard = <Guard state={state} message={message} />;
  if (state !== "ready") return guard;

  return (
    <section className="grid threeColumns">
      {meetings.length ? meetings.map((meeting) => (
        <article className="panel" key={meeting.id}>
          <p className="eyebrow">{meeting.type}</p>
          <h2>{meeting.title}</h2>
          <p>{new Date(meeting.scheduled_time).toLocaleString()}</p>
          <p>{meeting.agenda ?? "No agenda yet."}</p>
          <div className="buttonRow">
            {['accepted', 'tentative', 'declined'].map((status) => (
              <button className={status === 'accepted' ? 'primaryButton' : 'ghostButton'} disabled={Boolean(processing)} key={status} type="button" onClick={() => void rsvp(meeting.id, status)}>
                {processing === `${meeting.id}-${status}` ? 'Saving...' : status}
              </button>
            ))}
          </div>
        </article>
      )) : <StateBlock title="No meetings yet" message="Meetings created for your event will appear here." />}
    </section>
  );
}

export function BudgetClientPage() {
  const { project, state, message } = useFirstProject();
  const [budget, setBudget] = useState<BudgetResponse | null>(null);

  useEffect(() => {
    if (!project) return;
    void apiGet<BudgetResponse>(`/projects/${project.id}/budget`).then(setBudget).catch(() => setBudget(null));
  }, [project]);

  const guard = <Guard state={state} message={message} />;
  if (state !== "ready") return guard;
  if (!budget) return <StateBlock title="Budget unavailable" message="Your role may not have budget access for this event." />;

  return (
    <section className="grid twoColumns">
      <article className="panel">
        <p className="eyebrow">{budget.visibility.replaceAll('_', ' ')}</p>
        <h2>Budget View</h2>
        <p>Total: {budget.total == null ? 'Hidden' : `UGX ${budget.total.toLocaleString()}`}</p>
        <p>Spent: {budget.spent == null ? 'Hidden' : `UGX ${budget.spent.toLocaleString()}`}</p>
        <p>Remaining: {budget.remaining == null ? 'Hidden' : `UGX ${budget.remaining.toLocaleString()}`}</p>
      </article>
      <article className="panel">
        <h2>Contribution Progress</h2>
        <p>Paid: {budget.contribution_progress == null ? 'Hidden' : `UGX ${budget.contribution_progress.toLocaleString()}`}</p>
        <p>Pledged: {budget.pledged_total == null ? 'Hidden' : `UGX ${budget.pledged_total.toLocaleString()}`}</p>
      </article>
    </section>
  );
}

export function CommitteeClientPage() {
  const { project, state, message } = useFirstProject();
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    if (!project) return;
    void apiGet<Task[]>(`/projects/${project.id}/tasks`).then(setTasks).catch(() => setTasks([]));
  }, [project]);

  const guard = <Guard state={state} message={message} />;
  if (state !== "ready") return guard;

  return <section className="grid threeColumns">{tasks.length ? tasks.map((task) => <article className="panel" key={task.id}><p className="eyebrow">{task.status}</p><h2>{task.title}</h2><p>Due: {task.due_date ?? 'Not set'}</p></article>) : <StateBlock title="No tasks yet" message="Committee tasks will appear here once created." />}</section>;
}

export function VendorsClientPage() {
  const { project, state, message } = useFirstProject();
  const [vendors, setVendors] = useState<Vendor[]>([]);

  useEffect(() => {
    if (!project) return;
    void apiGet<Vendor[]>(`/projects/${project.id}/vendors`).then(setVendors).catch(() => setVendors([]));
  }, [project]);

  const guard = <Guard state={state} message={message} />;
  if (state !== "ready") return guard;

  return <section className="grid threeColumns">{vendors.length ? vendors.map((vendor) => <article className="panel" key={vendor.id}><p className="eyebrow">{vendor.category}</p><h2>{vendor.name}</h2><p>Status: {vendor.status}</p><p>Contact: {vendor.contact ?? 'Not set'}</p></article>) : <StateBlock title="No vendors yet" message="Vendor directory records will appear here once created." />}</section>;
}

export function StaffClientPage() {
  const [state, setState] = useState<"anonymous" | "loading" | "ready" | "denied" | "error">("loading");
  const [dashboard, setDashboard] = useState<StaffDashboard | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) { setState("anonymous"); return; }
    void apiGet<StaffDashboard>("/staff/dashboard", token)
      .then((data) => { setDashboard(data); setState("ready"); })
      .catch((error) => { setState(error && typeof error === 'object' && 'status' in error && error.status === 403 ? "denied" : "error"); });
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
