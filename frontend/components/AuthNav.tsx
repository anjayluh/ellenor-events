"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import { clearSession, consumeSessionNotice, getSessionUser, subscribeToAuthChanges } from "../lib/session";
import type { AuthUser } from "../lib/types";

export function AuthNav() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [notice, setNotice] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const sync = (detail?: { message?: string }) => {
      const nextUser = getSessionUser();
      setUser(nextUser);
      setIsReady(true);
      setNotice(nextUser ? "" : detail?.message || consumeSessionNotice());
      setIsAdmin(false);
      if (!nextUser) {
        return;
      }
      void apiGet("/admin/me")
        .then(() => setIsAdmin(true))
        .catch(() => setIsAdmin(false));
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
      <div className={`navCluster ${menuOpen ? "menuOpen" : ""}`}>
        {notice ? <span className="sessionNotice" role="status">{notice}</span> : null}
        <button className="navToggle" type="button" aria-expanded={menuOpen} aria-controls="public-navigation" onClick={() => setMenuOpen((open) => !open)}>
          {menuOpen ? "Close" : "Menu"}
        </button>
        <nav className="nav" id="public-navigation" aria-label="Public navigation">
          <Link href="/" onClick={() => setMenuOpen(false)}>Home</Link>
          <Link href="/packages" onClick={() => setMenuOpen(false)}>Packages</Link>
          <Link className="navCta" href="/login" onClick={() => setMenuOpen(false)}>Sign in</Link>
        </nav>
      </div>
    );
  }

  return (
    <div className={`navCluster ${menuOpen ? "menuOpen" : ""}`}>
      <button className="navToggle" type="button" aria-expanded={menuOpen} aria-controls="account-navigation" onClick={() => setMenuOpen((open) => !open)}>
        {menuOpen ? "Close" : "Menu"}
      </button>
      <nav className="nav" id="account-navigation" aria-label="Account navigation">
        <Link href="/" onClick={() => setMenuOpen(false)}>Dashboard</Link>
        <Link href="/#events" onClick={() => setMenuOpen(false)}>My Events</Link>
        <Link href="/packages" onClick={() => setMenuOpen(false)}>Packages</Link>
        <Link href="/billing" onClick={() => setMenuOpen(false)}>Billing</Link>
        <Link href="/vendor-marketplace" onClick={() => setMenuOpen(false)}>Marketplace</Link>
        {isAdmin ? <Link href="/admin" onClick={() => setMenuOpen(false)}>Team area</Link> : null}
        <button
          className="navButton"
          type="button"
          onClick={() => {
            clearSession();
            setMenuOpen(false);
            router.replace("/");
          }}
        >
          Sign out
        </button>
      </nav>
    </div>
  );
}
