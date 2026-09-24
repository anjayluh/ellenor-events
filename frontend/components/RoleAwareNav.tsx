import Link from "next/link";
import type { ProjectRole } from "../lib/types";

const roleLinks: Record<ProjectRole, Array<{ href: string; label: string }>> = {
  OWNER: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" },
    { href: "budget", label: "Budget" },
    { href: "committee", label: "Tasks" },
    { href: "vendors", label: "Vendors" },
    { href: "invites", label: "Team Access" },
    { href: "guest-invites", label: "Guest RSVPs" }
  ],
  PARTNER: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" },
    { href: "budget", label: "Budget" },
    { href: "committee", label: "Tasks" },
    { href: "vendors", label: "Vendors" },
    { href: "invites", label: "Team Access" },
    { href: "guest-invites", label: "Guest RSVPs" }
  ],
  COMMITTEE_CHAIR: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" },
    { href: "budget", label: "Budget Summary" },
    { href: "committee", label: "Tasks" },
    { href: "vendors", label: "Vendors" },
    { href: "invites", label: "Team Access" },
    { href: "guest-invites", label: "Guest RSVPs" }
  ],
  COMMITTEE_MEMBER: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" },
    { href: "committee", label: "Tasks" },
    { href: "vendors", label: "Vendors" }
  ],
  FAMILY_VIEWER: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" },
    { href: "budget", label: "Contributions" }
  ],
  GUEST_VIEWER: [
    { href: "overview", label: "Overview" },
    { href: "details", label: "Event Details" },
    { href: "meetings", label: "Meetings" }
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
