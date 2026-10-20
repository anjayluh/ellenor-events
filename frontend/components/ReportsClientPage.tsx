"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ActiveEventSwitcher } from "./ActiveEventSwitcher";
import { RoleAwareNav } from "./RoleAwareNav";
import { StateBlock } from "./StateBlock";
import { apiDownload, apiGet } from "../lib/api";
import { formatDate } from "../lib/customer-display";
import { useActiveProject } from "../lib/useActiveProject";
import type { ReportSummary } from "../lib/types";

const exportOptions = [
  ["guests", "Guests"], ["budget", "Budget"], ["vendors", "Vendors"], ["tasks", "Tasks"],
  ["timeline", "Timeline"], ["meetings", "Meetings"], ["decisions", "Decisions"]
] as const;

function money(value: string | number | null | undefined) {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-UG", { style: "currency", currency: "UGX", maximumFractionDigits: 0 }).format(Number(value));
}

export function ReportsClientPage() {
  const { projects, project, state, message, selectProject } = useActiveProject();
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    if (!project) return;
    let mounted = true;
    setError("");
    void apiGet<ReportSummary>(`/projects/${project.id}/reports/summary`).then((data) => {
      if (mounted) setSummary(data);
    }).catch((requestError: unknown) => {
      if (mounted) setError(requestError instanceof Error ? requestError.message : "Could not load the event report.");
    });
    return () => { mounted = false; };
  }, [project]);

  async function download(path: string, key: string) {
    if (!project || downloading) return;
    setDownloading(key);
    try {
      const result = await apiDownload(`/projects/${project.id}/reports/${path}`);
      const link = document.createElement("a");
      link.href = URL.createObjectURL(result.blob);
      link.download = result.filename ?? `${project.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${key}`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (requestError: unknown) {
      setError(requestError instanceof Error ? requestError.message : "Could not download that report.");
    } finally {
      setDownloading(null);
    }
  }

  if (state === "anonymous") return <StateBlock title="Sign in to view reports" message="Your event reports are private to the planning team." />;
  if (state === "loading") return <StateBlock title="Loading your events" message="Preparing the report workspace..." />;
  if (state === "empty") return <StateBlock title="No event yet" message="Create or join an event to see its planning report." />;
  if (state === "selection_required") return <><ActiveEventSwitcher projects={projects} onChange={selectProject} /><StateBlock title="Choose an event" message={message || "Select the event you want to review."} /></>;
  if (state === "error" || !project) return <StateBlock title="Reports unavailable" message={message || "Could not load the selected event."} />;

  return <>
    <ActiveEventSwitcher projects={projects} activeProjectId={project.id} onChange={selectProject} />
    <RoleAwareNav role={project.role ?? "FAMILY_VIEWER"} projectId={project.id} />
    {error ? <div className="errorText" role="alert">{error}</div> : null}
    <section className="panel resourceCard">
      <div className="sectionHeaderRow"><div><p className="eyebrow">{summary?.title ?? project.title}</p><h2>Planning report</h2><p>{summary?.event_date ? `Event date: ${formatDate(summary.event_date)}` : "Event date to be confirmed"}</p></div><span className="badge softBadge">Read only</span></div>
      <div className="buttonRow"><button className="primaryButton" type="button" disabled={Boolean(downloading)} onClick={() => void download("export.pdf", "event-report.pdf")}>{downloading === "pdf" ? "Preparing..." : "Download PDF"}</button><Link className="ghostButton" href={`/events/${project.id}`}>Back to event</Link></div>
    </section>
    {summary ? <>
      <section className="grid fourColumns">
        <article className="metric"><span>Guests</span><strong>{summary.guests?.total ?? "—"}</strong><p>{summary.guests ? `${summary.guests.attending} attending · ${summary.guests.pending} pending` : "Not visible for this role"}</p></article>
        <article className="metric"><span>Budget</span><strong>{summary.budget ? money(summary.budget.total_planned) : "—"}</strong><p>{summary.budget ? `${money(summary.budget.total_paid)} paid · ${money(summary.budget.total_outstanding)} outstanding` : "Not visible for this role"}</p></article>
        <article className="metric"><span>Vendors</span><strong>{summary.vendors?.total ?? "—"}</strong><p>{summary.vendors ? `${summary.vendors.confirmed} confirmed · ${summary.vendors.needs_attention} to review` : "No vendor summary yet"}</p></article>
        <article className="metric"><span>Tasks</span><strong>{summary.tasks?.total ?? "—"}</strong><p>{summary.tasks ? `${summary.tasks.completed} complete · ${summary.tasks.overdue} overdue` : "No task summary yet"}</p></article>
      </section>
      <section className="grid twoColumns">
        <article className="panel resourceCard"><p className="eyebrow">Schedule</p><h2>Timeline &amp; meetings</h2><p>{summary.timeline ? `${summary.timeline.upcoming} upcoming timeline items · ${summary.timeline.conflicts} conflicts` : "No timeline data yet."}</p><p>{summary.meetings ? `${summary.meetings.summary.upcoming} upcoming meetings · ${summary.meetings.decisions} decisions recorded` : "No meeting data yet."}</p><div className="buttonRow"><Link className="ghostButton" href={`/timeline?project=${project.id}`}>View timeline</Link><Link className="ghostButton" href={`/meetings?project=${project.id}`}>View meetings</Link></div></article>
        <article className="panel resourceCard"><p className="eyebrow">Team record</p><h2>Documents &amp; communications</h2><p>{summary.documents ? `${summary.documents.active} active documents · ${summary.documents.archived} archived` : "Documents are not visible for this role."}</p><p>{summary.communications ? `${summary.communications.unread_count} unread · ${summary.communications.pinned_count} pinned communications` : "No communications summary yet."}</p><div className="buttonRow"><Link className="ghostButton" href={`/documents?project=${project.id}`}>View documents</Link><Link className="ghostButton" href={`/communications?project=${project.id}`}>View communications</Link></div></article>
      </section>
      <section className="panel tablePanel"><div className="sectionHeader"><div><p className="eyebrow">Exports</p><h2>Take the planning record with you</h2></div><span className="badge softBadge">CSV</span></div><p>Download focused spreadsheets for the planning areas you need to share or review.</p><div className="quickActionGrid">{exportOptions.map(([key, label]) => <button className="ghostButton" type="button" key={key} disabled={Boolean(downloading)} onClick={() => void download(`exports/${key}.csv`, `${key}.csv`)}>{downloading === key ? "Preparing..." : `${label} CSV`}</button>)}</div></section>
    </> : <StateBlock title="Report is loading" message="Gathering the latest event planning information..." />}
  </>;
}
