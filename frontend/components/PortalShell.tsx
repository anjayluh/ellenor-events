import Link from "next/link";
import Image from "next/image";
import { AuthNav } from "./AuthNav";

export function PortalShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="shell">
      <header className="header">
        <Link className="brand" href="/">
          <Image className="brandLogo" src="/assets/ellenor-events-logo-64.png" alt="" width={44} height={44} priority />
          <span>Ellenor Events</span>
        </Link>
        <AuthNav />
      </header>
      <main className="main">{children}</main>
    </div>
  );
}
