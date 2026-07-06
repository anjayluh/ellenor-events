import { PortalShell } from "../../components/PortalShell";
import { staffDashboard } from "../../lib/staff-demo";

export default function StaffPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Staff Portal</p>
        <h1>Project health, risk alerts, and RSVP movement.</h1>
        <p>Internal-only oversight uses staff roles, separate from client project roles.</p>
      </section>

      <section className="grid threeColumns">
        <article className="metric"><span>Active projects</span><strong>{staffDashboard.active_projects}</strong></article>
        <article className="metric"><span>Accepted RSVPs</span><strong>{staffDashboard.rsvp_summary.accepted}</strong></article>
        <article className="metric"><span>Risk alerts</span><strong>{staffDashboard.risk_alerts.length}</strong></article>
      </section>

      <section className="grid twoColumns">
        <article className="panel">
          <h2>Risk Alerts</h2>
          <div className="stack">
            {staffDashboard.risk_alerts.map((alert) => (
              <div className="eventCard" key={`${alert.title}-${alert.message}`}>
                <p className="eyebrow">{alert.severity}</p>
                <h3>{alert.title}</h3>
                <p>{alert.message}</p>
              </div>
            ))}
          </div>
        </article>
        <article className="panel">
          <h2>Project Health</h2>
          <div className="stack">
            {staffDashboard.project_health.map((project) => (
              <div className="eventCard" key={project.title}>
                <p className="eyebrow">{project.risk_level} risk</p>
                <h3>{project.title}</h3>
                <p>{project.pending_task_count} pending task(s), {project.overdue_task_count} overdue.</p>
                <p>{project.meeting_count} meeting(s), budget variance {(project.budget_variance * 100).toFixed(0)}%.</p>
              </div>
            ))}
          </div>
        </article>
      </section>
    </PortalShell>
  );
}
