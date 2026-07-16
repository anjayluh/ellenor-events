import Link from "next/link";
import { AuthNav } from "./AuthNav";

export function PortalShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="shell">
      <header className="header">
        <Link className="brand" href="/">Ellenor Events</Link>
        <AuthNav />
      </header>
      <main className="main">{children}</main>
    </div>
  );
}
