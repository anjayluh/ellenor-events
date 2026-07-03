import { EventDashboard } from "../../../components/EventDashboard";
import { PortalShell } from "../../../components/PortalShell";
import { StateBlock } from "../../../components/StateBlock";
import { apiGet } from "../../../lib/api";
import { demoProjects } from "../../../lib/demo-data";
import type { Project } from "../../../lib/types";

type EventPageProps = {
  params: Promise<{ projectId: string }>;
};

async function getProject(projectId: string): Promise<Project | null> {
  try {
    return await apiGet<Project>(`/projects/${projectId}`);
  } catch {
    return demoProjects.find((project) => project.id === projectId) ?? null;
  }
}

export default async function EventPage({ params }: EventPageProps) {
  const { projectId } = await params;
  const project = await getProject(projectId);

  return (
    <PortalShell>
      {project ? (
        <EventDashboard project={project} />
      ) : (
        <StateBlock title="Event not found" message="The event could not be loaded from the API or demo data." />
      )}
    </PortalShell>
  );
}
