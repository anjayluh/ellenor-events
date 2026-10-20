import Link from "next/link";
import type { ProjectRole } from "../lib/types";

const roleLinks: Record<ProjectRole, Array<{ href: string; label: string }>> = {
  OWNER: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" },
    { href: "timeline", label: "Timeline" },
    { href: "budget", label: "Budget" },
    { href: "tasks", label: "Tasks" },
    { href: "vendors", label: "Vendors" },
    { href: "invites", label: "Team Access" },
    { href: "guests", label: "Guests" },
    { href: "communications", label: "Communications" }
    ,{ href: "documents", label: "Documents" },{ href: "reports", label: "Reports" }
  ],
  PARTNER: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" },
    { href: "timeline", label: "Timeline" },
    { href: "budget", label: "Budget" },
    { href: "tasks", label: "Tasks" },
    { href: "vendors", label: "Vendors" },
    { href: "invites", label: "Team Access" },
    { href: "guests", label: "Guests" },
    { href: "communications", label: "Communications" }
    ,{ href: "documents", label: "Documents" },{ href: "reports", label: "Reports" }
  ],
  COMMITTEE_CHAIR: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" },
    { href: "timeline", label: "Timeline" },
    { href: "budget", label: "Budget Summary" },
    { href: "tasks", label: "Tasks" },
    { href: "vendors", label: "Vendors" },
    { href: "invites", label: "Team Access" },
    { href: "guests", label: "Guests" },
    { href: "communications", label: "Communications" }
    ,{ href: "documents", label: "Documents" },{ href: "reports", label: "Reports" }
  ],
  COMMITTEE_MEMBER: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" },
    { href: "timeline", label: "Timeline" },
    { href: "tasks", label: "Tasks" },
    { href: "vendors", label: "Vendors" },
    { href: "communications", label: "Communications" }
    ,{ href: "documents", label: "Documents" },{ href: "reports", label: "Reports" }
  ],
  FAMILY_VIEWER: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" },
    { href: "timeline", label: "Timeline" },
    { href: "budget", label: "Contributions" },
    { href: "communications", label: "Communications" }
    ,{ href: "documents", label: "Documents" },{ href: "reports", label: "Reports" }
  ],
  GUEST_VIEWER: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" },
    { href: "timeline", label: "Timeline" },
    { href: "reports", label: "Reports" }
  ]
};

export function RoleAwareNav({ role, projectId }: { role: ProjectRole; projectId: string }) {
  const hrefFor = (href: string) => {
    if (href === "overview") return `/events/${projectId}`;
    if (href === "details") return `/events/${projectId}#event-details`;
    return `/${href}?project=${projectId}`;
  };

  return (
    <nav className="tabNav" aria-label="Event dashboard sections">
      {roleLinks[role].map((link) => (
        <Link href={hrefFor(link.href)} key={link.href}>{link.label}</Link>
      ))}
    </nav>
  );
}
