import Link from "next/link";
import type { ProjectRole } from "../lib/types";

const roleLinks: Record<ProjectRole, Array<{ href: string; label: string }>> = {
  OWNER: [
    { href: "overview", label: "Overview" },
    { href: "meetings", label: "Meetings" },
    { href: "budget", label: "Budget" },
    { href: "committee", label: "Committee" },
    { href: "vendors", label: "Vendors" },
    { href: "timeline", label: "Timeline" }
  ],
  PARTNER: [
    { href: "overview", label: "Overview" },
    { href: "meetings", label: "Meetings" },
    { href: "budget", label: "Budget" },
    { href: "committee", label: "Committee" },
    { href: "vendors", label: "Vendors" },
    { href: "timeline", label: "Timeline" }
  ],
  COMMITTEE_CHAIR: [
    { href: "overview", label: "Overview" },
    { href: "meetings", label: "Meetings" },
    { href: "budget", label: "Budget Summary" },
    { href: "committee", label: "Committee" },
    { href: "vendors", label: "Vendors" }
  ],
  COMMITTEE_MEMBER: [
    { href: "overview", label: "Overview" },
    { href: "meetings", label: "Meetings" },
    { href: "committee", label: "Tasks" },
    { href: "vendors", label: "Vendors" }
  ],
  FAMILY_VIEWER: [
    { href: "overview", label: "Overview" },
    { href: "meetings", label: "Meetings" },
    { href: "budget", label: "Contributions" }
  ],
  GUEST_VIEWER: [
    { href: "overview", label: "Overview" },
    { href: "meetings", label: "Meetings" }
  ]
};

export function RoleAwareNav({ role, projectId }: { role: ProjectRole; projectId: string }) {
  return (
    <nav className="tabNav" aria-label="Event dashboard sections">
      {roleLinks[role].map((link) => (
        <Link href={`/events/${projectId}#${link.href}`} key={link.href}>{link.label}</Link>
      ))}
    </nav>
  );
}
