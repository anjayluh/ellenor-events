"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import { clearSession, consumeSessionNotice, getSessionUser, subscribeToAuthChanges } from "../lib/session";
import type { AuthUser } from "../lib/types";

export function AuthNav() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [notice, setNotice] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const sync = (detail?: { message?: string }) => {
      const nextUser = getSessionUser();
      setUser(nextUser);
      setNotice(nextUser ? "" : detail?.message || consumeSessionNotice());
      setIsAdmin(false);
      if (nextUser) void apiGet("/admin/me").then(() => setIsAdmin(true)).catch(() => setIsAdmin(false));
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
      <Link href="/vendor-marketplace">Vendor Marketplace</Link>
      <Link href="/vendor-portal">Vendor Portal</Link>
      {isAdmin ? <Link href="/admin">Admin</Link> : null}
      <button className="navButton" type="button" onClick={() => clearSession()}>Logout</button>
    </nav>
  );
}
