import { BudgetPreview } from "./BudgetPreview";
import { RoleAwareNav } from "./RoleAwareNav";
import type { Project } from "../lib/types";

export function EventDashboard({ project }: { project: Project }) {
  const role = project.role ?? "FAMILY_VIEWER";
  const visibility = project.budget_visibility_mode ?? "NO_ACCESS";

  return (
    <>
      <section className="hero compact">
        <p className="eyebrow">{project.type} dashboard</p>
        <h1>{project.title}</h1>
        <p>
          Role: {role.replaceAll("_", " ")} · Event date: {project.event_date ?? "To be confirmed"}
        </p>
      </section>

      <RoleAwareNav role={role} projectId={project.id} />

      <section className="grid twoColumns" id="overview">
        <article className="panel">
          <p className="eyebrow">Overview</p>
          <h2>Coordination Snapshot</h2>
          <p>Status: {project.status}</p>
          <p>Use the tabs above to view live meetings, committee tasks, vendors, and budget areas allowed for your role.</p>
        </article>
        <BudgetPreview visibility={visibility} />
      </section>
    </>
  );
}
