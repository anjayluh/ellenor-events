"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { BudgetPreview } from "./BudgetPreview";
import { RoleAwareNav } from "./RoleAwareNav";
import { apiGet, apiPatch, apiPost } from "../lib/api";
import { formatDate } from "../lib/customer-display";
import type { BudgetResponse, Project, ProjectRole } from "../lib/types";

const EVENT_ADMIN_ROLES: ProjectRole[] = ["OWNER", "PARTNER", "COMMITTEE_CHAIR"];
const EVENT_ARCHIVE_ROLES: ProjectRole[] = ["OWNER", "PARTNER"];
const COORDINATOR_ROLES: ProjectRole[] = ["OWNER", "PARTNER", "COMMITTEE_CHAIR", "COMMITTEE_MEMBER"];

type Task = { id: string; title: string; status: string; due_date?: string | null };
type Vendor = { id: string; name: string; category: string; status: string };
type Meeting = { id: string; title: string; scheduled_time: string; status: string };
type Member = { id: string; role: ProjectRole };
type GuestInviteSummary = { total: number; sent: number; accepted: number; declined: number; pending: number; rejected: number };
type InviteAnalytics = { pending: number; accepted: number; expired: number; cancelled: number; total_sent: number; total_opened: number };
type EventOverviewData = {
  budget: BudgetResponse | null;
  guestSummary: GuestInviteSummary | null;
  inviteAnalytics: InviteAnalytics | null;
  meetings: Meeting[];
  members: Member[];
  tasks: Task[];
  vendors: Vendor[];
};

const emptyOverviewData: EventOverviewData = {
  budget: null,
  guestSummary: null,
  inviteAnalytics: null,
  meetings: [],
  members: [],
  tasks: [],
  vendors: []
};

async function safeGet<T>(path: string, fallback: T): Promise<T> {
  try {
    return await apiGet<T>(path);
  } catch {
    return fallback;
  }
}

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatMoney(value?: number | null) {
  if (value == null) return "Not set";
  return new Intl.NumberFormat("en-UG", { style: "currency", currency: "UGX", maximumFractionDigits: 0 }).format(value);
}

function isOverdue(task: Task) {
  if (!task.due_date || task.status === "done") return false;
  const dueDate = new Date(`${task.due_date}T23:59:59`);
  return dueDate.getTime() < Date.now();
}

function hasPermission(role: ProjectRole, permissions: string[], allowedRoles: ProjectRole[], permission?: string) {
  return allowedRoles.includes(role) || Boolean(permission && permissions.includes(permission));
}

export function EventDashboard({ project }: { project: Project }) {
  const [currentProject, setCurrentProject] = useState(project);
  const [overviewData, setOverviewData] = useState<EventOverviewData>(emptyOverviewData);
  const [title, setTitle] = useState(project.title);
  const [eventDate, setEventDate] = useState(project.event_date ?? "");
  const [message, setMessage] = useState("Event owners and leads can keep the core event details up to date.");
  const [processing, setProcessing] = useState<string | null>(null);
  const role = currentProject.role ?? "FAMILY_VIEWER";
  const visibility = currentProject.budget_visibility_mode ?? "NO_ACCESS";
  const permissions = currentProject.permissions ?? [];
  const canEditEvent = EVENT_ADMIN_ROLES.includes(role);
  const canArchiveEvent = EVENT_ARCHIVE_ROLES.includes(role);
  const canCoordinate = COORDINATOR_ROLES.includes(role);
  const canManageTeam = hasPermission(role, permissions, EVENT_ADMIN_ROLES, "committee.manage");
  const canManageGuests = hasPermission(role, permissions, EVENT_ADMIN_ROLES, "guest_invites.manage");
  const canManageVendors = hasPermission(role, permissions, EVENT_ADMIN_ROLES, "vendors.manage");
  const canEditBudget = hasPermission(role, permissions, ["OWNER", "PARTNER"], "budget.edit");
  const titleError = title && title.trim().length < 4 ? "Event title must be at least 4 characters." : "";
  const eventChanged = title.trim() !== currentProject.title || (eventDate || null) !== currentProject.event_date;
  const canSave = canEditEvent && eventChanged && title.trim().length >= 4 && !titleError;

  useEffect(() => {
    let isMounted = true;
    const projectId = currentProject.id;
    async function loadOverview() {
      const [budget, guestSummary, inviteAnalytics, meetings, members, tasks, vendors] = await Promise.all([
        safeGet<BudgetResponse | null>(`/projects/${projectId}/budget`, null),
        safeGet<GuestInviteSummary | null>(`/projects/${projectId}/guest-invites/summary`, null),
        safeGet<InviteAnalytics | null>(`/invites/projects/${projectId}/analytics`, null),
        safeGet<Meeting[]>(`/projects/${projectId}/meetings`, []),
        safeGet<Member[]>(`/projects/${projectId}/members`, []),
        safeGet<Task[]>(`/projects/${projectId}/tasks`, []),
        safeGet<Vendor[]>(`/projects/${projectId}/vendors`, [])
      ]);
      if (isMounted) {
        setOverviewData({ budget, guestSummary, inviteAnalytics, meetings, members, tasks, vendors });
      }
    }
    void loadOverview();
    return () => {
      isMounted = false;
    };
  }, [currentProject.id]);

  const upcomingMeetings = useMemo(() => overviewData.meetings.filter((meeting) => new Date(meeting.scheduled_time).getTime() >= Date.now()).slice(0, 3), [overviewData.meetings]);
  const overdueTasks = overviewData.tasks.filter(isOverdue);
  const pendingTasks = overviewData.tasks.filter((task) => task.status !== "done");
  const completedTasks = overviewData.tasks.filter((task) => task.status === "done");
  const vendorsNeedingDecision = overviewData.vendors.filter((vendor) => !["booked", "rejected"].includes(vendor.status));
  const bookedVendors = overviewData.vendors.filter((vendor) => vendor.status === "booked");
  const budgetBalance = overviewData.budget?.line_item_balance_total ?? overviewData.budget?.remaining ?? null;
  const planningAreas = [
    { label: "Guests", hasData: Boolean(overviewData.guestSummary?.total) },
    { label: "Vendors", hasData: overviewData.vendors.length > 0 },
    { label: "Tasks", hasData: overviewData.tasks.length > 0 },
    { label: "Budget", hasData: Boolean((overviewData.budget?.total ?? 0) > 0 || (overviewData.budget?.line_item_total_cost ?? 0) > 0) },
    { label: "Meetings", hasData: overviewData.meetings.length > 0 },
    { label: "Team", hasData: overviewData.members.length > 0 || Boolean(overviewData.inviteAnalytics?.pending || overviewData.inviteAnalytics?.accepted) }
  ];
  const activePlanningAreas = planningAreas.filter((area) => area.hasData);
  const attentionItems = [
    ...overdueTasks.slice(0, 2).map((task) => ({ title: task.title, detail: `Task overdue since ${formatDate(task.due_date)}`, href: `/committee?project=${currentProject.id}` })),
    ...upcomingMeetings.slice(0, 2).map((meeting) => ({ title: meeting.title, detail: `Meeting on ${formatDate(meeting.scheduled_time)}`, href: `/meetings?project=${currentProject.id}` })),
    ...(overviewData.guestSummary && overviewData.guestSummary.pending > 0 ? [{ title: `${overviewData.guestSummary.pending} guest response${overviewData.guestSummary.pending === 1 ? "" : "s"} pending`, detail: "Review invitation responses.", href: `/guest-invites?project=${currentProject.id}` }] : []),
    ...(vendorsNeedingDecision.length ? [{ title: `${vendorsNeedingDecision.length} vendor decision${vendorsNeedingDecision.length === 1 ? "" : "s"} open`, detail: "Review vendor stages and next steps.", href: `/vendors?project=${currentProject.id}` }] : []),
    ...(budgetBalance && budgetBalance > 0 ? [{ title: `${formatMoney(budgetBalance)} still awaiting payment`, detail: "Review budget deposits and balances.", href: `/budget?project=${currentProject.id}` }] : [])
  ].slice(0, 5);

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
      <section className="hero compact eventHero">
        <div>
          <p className="eyebrow">{titleCase(currentProject.type)} workspace</p>
          <h1>{currentProject.title}</h1>
          <div className="eventHeroMeta">
            <span>{currentProject.event_date ? formatDate(currentProject.event_date) : "Date to be confirmed"}</span>
            <span>{currentProject.status === "archived" ? "Archived" : "Active planning"}</span>
            <span>{titleCase(role)}</span>
          </div>
          <p>This is the central planning space for your event. Use it to open the right planning area, check what needs attention, and keep core event details current.</p>
        </div>
        <div className="eventHeroActions">
          {canEditEvent ? <a className="secondaryButton" data-icon="✎" href="#event-details">Edit event</a> : null}
          <Link className="primaryButton" data-icon="→" href={`/meetings?project=${currentProject.id}`}>Open planning tools</Link>
        </div>
      </section>

      <RoleAwareNav role={role} projectId={currentProject.id} />

      <section className="grid fourColumns eventMetricGrid" id="overview">
        <article className="metric eventMetric">
          <span>Guests</span>
          <strong>{overviewData.guestSummary ? overviewData.guestSummary.total : "—"}</strong>
          <p>{overviewData.guestSummary ? `${overviewData.guestSummary.sent} sent · ${overviewData.guestSummary.accepted} accepted` : "Guest invitations will appear once added."}</p>
        </article>
        <article className="metric eventMetric">
          <span>Vendors</span>
          <strong>{overviewData.vendors.length}</strong>
          <p>{overviewData.vendors.length ? `${bookedVendors.length} booked · ${vendorsNeedingDecision.length} needing attention` : "Vendor options will appear once added."}</p>
        </article>
        <article className="metric eventMetric">
          <span>Tasks</span>
          <strong>{overviewData.tasks.length}</strong>
          <p>{overviewData.tasks.length ? `${completedTasks.length} done · ${pendingTasks.length} pending` : "Planning tasks will appear once added."}</p>
        </article>
        <article className="metric eventMetric">
          <span>Budget</span>
          <strong>{budgetBalance == null ? "—" : formatMoney(budgetBalance)}</strong>
          <p>{overviewData.budget ? `Planned ${formatMoney(overviewData.budget.line_item_total_cost ?? overviewData.budget.total)}` : "Budget details depend on your access."}</p>
        </article>
      </section>

      <section className="grid twoColumns">
        <article className="panel resourceCard overviewPanel">
          <p className="eyebrow">Overview</p>
          <h2>Coordination snapshot</h2>
          <p>Status: {currentProject.status === "archived" ? "Archived — no longer in active planning" : "Active planning"}</p>
          <div className="planningAreaList">
            {planningAreas.map((area) => (
              <span className={area.hasData ? "badge successBadge" : "badge softBadge"} key={area.label}>{area.hasData ? "✓" : "•"} {area.label}</span>
            ))}
          </div>
          {activePlanningAreas.length ? (
            <p>{activePlanningAreas.length} planning area{activePlanningAreas.length === 1 ? "" : "s"} already contain real event activity.</p>
          ) : (
            <p>Start adding your planning items to track progress here. No percentage is shown until there is enough real planning data.</p>
          )}
          <div className="quickActionGrid">
            <Link className="ghostButton" data-icon="↗" href={`/meetings?project=${currentProject.id}`}>Meetings</Link>
            {canEditBudget || visibility !== "NO_ACCESS" ? <Link className="ghostButton" data-icon="↗" href={`/budget?project=${currentProject.id}`}>{canEditBudget ? "Manage budget" : "View budget"}</Link> : null}
            {canManageGuests ? <Link className="ghostButton" data-icon="↗" href={`/guest-invites?project=${currentProject.id}`}>Guest RSVPs</Link> : null}
            {canManageVendors ? <Link className="ghostButton" data-icon="↗" href={`/vendors?project=${currentProject.id}`}>Vendors</Link> : null}
            {canCoordinate ? <Link className="ghostButton" data-icon="↗" href={`/committee?project=${currentProject.id}`}>Tasks</Link> : null}
            {canManageTeam ? <Link className="ghostButton" data-icon="↗" href={`/invites?project=${currentProject.id}`}>Members</Link> : null}
          </div>
        </article>

        <article className="panel resourceCard attentionPanel">
          <p className="eyebrow">Needs attention</p>
          <h2>Upcoming and open items</h2>
          {attentionItems.length ? (
            <div className="attentionList">
              {attentionItems.map((item) => (
                <Link className="attentionItem" href={item.href} key={`${item.href}-${item.title}`}>
                  <strong>{item.title}</strong>
                  <span>{item.detail}</span>
                </Link>
              ))}
            </div>
          ) : (
            <p>No urgent planning items are visible yet. Upcoming meetings, overdue tasks, pending guests, vendor decisions, and payment balances will appear here when those records exist.</p>
          )}
        </article>
      </section>

      <section className="grid twoColumns">
        <BudgetPreview visibility={visibility} />
        <article className="panel actionPanel resourceCard" id="event-details">
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
          ) : <p>You can view this event, but editing event details is not enabled for your account.</p>}
          <p>{message}</p>
        </article>
      </section>
    </>
  );
}
