"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { clearSession, getSessionUser, subscribeToAuthChanges } from "../lib/session";
import type { AuthUser } from "../lib/types";

export function AuthNav() {
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const sync = () => setUser(getSessionUser());
    sync();
    return subscribeToAuthChanges(sync);
  }, []);

  if (!user) {
    return (
      <nav className="nav" aria-label="Public navigation">
        <Link href="/">Home</Link>
        <Link href="/login">Login</Link>
      </nav>
    );
  }

  return (
    <nav className="nav" aria-label="Authenticated navigation">
      <Link href="/">My Events</Link>
      <Link href="/meetings">Meetings</Link>
      <Link href="/budget">Budget</Link>
      <Link href="/committee">Committee</Link>
      <Link href="/vendors">Vendors</Link>
      <Link href="/invites">Invites</Link>
      <button className="navButton" type="button" onClick={clearSession}>Logout</button>
    </nav>
  );
}
