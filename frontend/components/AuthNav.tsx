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
  const [isReady, setIsReady] = useState(false);
  const [adminChecked, setAdminChecked] = useState(false);

  useEffect(() => {
    const sync = (detail?: { message?: string }) => {
      const nextUser = getSessionUser();
      setUser(nextUser);
      setIsReady(true);
      setNotice(nextUser ? "" : detail?.message || consumeSessionNotice());
      if (!nextUser) {
        setIsAdmin(false);
        setAdminChecked(true);
        return;
      }
      setAdminChecked(false);
      void apiGet("/admin/me")
        .then(() => setIsAdmin(true))
        .catch(() => setIsAdmin(false))
        .finally(() => setAdminChecked(true));
    };
    sync();
    return subscribeToAuthChanges(sync);
  }, []);

  if (!isReady) {
    return (
      <nav className="nav stableNav" aria-label="Checking session">
        <span>Checking session…</span>
      </nav>
    );
  }

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
    <nav className="nav" aria-label="Account navigation">
      <Link href="/">My Events</Link>
      <Link href="/vendor-marketplace">Vendor Marketplace</Link>
      <Link href="/vendor-portal">Vendor Portal</Link>
      {isAdmin ? <Link href="/admin">Admin</Link> : null}
      {!adminChecked ? <span className="navPlaceholder">Admin</span> : null}
      <button className="navButton" type="button" onClick={() => clearSession()}>Logout</button>
    </nav>
  );
}
