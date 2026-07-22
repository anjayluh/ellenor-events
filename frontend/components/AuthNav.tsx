"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { clearSession, consumeSessionNotice, getSessionUser, subscribeToAuthChanges } from "../lib/session";
import type { AuthUser } from "../lib/types";

export function AuthNav() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const sync = (detail?: { message?: string }) => {
      const nextUser = getSessionUser();
      setUser(nextUser);
      setNotice(nextUser ? "" : detail?.message || consumeSessionNotice());
    };
    sync();
    return subscribeToAuthChanges(sync);
  }, []);

  if (!user) {
    return (
      <div className="navCluster">
        {notice ? <span className="sessionNotice" role="status">{notice}</span> : null}
        <nav className="nav" aria-label="Public navigation">
          <Link href="/">Home</Link>
          <Link href="/login">Login</Link>
        </nav>
      </div>
    );
  }

  return (
    <nav className="nav" aria-label="Authenticated navigation">
      <Link href="/">My Events</Link>
      <button className="navButton" type="button" onClick={() => clearSession()}>Logout</button>
    </nav>
  );
}
