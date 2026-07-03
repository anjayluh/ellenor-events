import Link from "next/link";

export function PortalShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="shell">
      <header className="header">
        <Link className="brand" href="/">Ellenor Events</Link>
        <nav className="nav">
          <Link href="/">Client Portal</Link>
          <Link href="/meetings">Meetings</Link>
          <Link href="/budget">Budget</Link>
          <Link href="/committee">Committee</Link>
          <Link href="/vendors">Vendors</Link>
          <Link href="/staff">Staff Portal</Link>
        </nav>
      </header>
      <main className="main">{children}</main>
    </div>
  );
}
