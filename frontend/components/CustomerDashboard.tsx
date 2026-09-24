"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiGet } from "../lib/api";
import { setActiveProjectId } from "../lib/active-project";
import { activeSubscription, customerStatusLabel, entitlementName, entitlementQuantity, formatAmount, formatBillingInterval, formatDate, sortEntitlementKeys } from "../lib/customer-display";
import { cacheProjects } from "../lib/project-cache";
import { getAccessToken, getSessionUser, subscribeToAuthChanges } from "../lib/session";
import type { AccountEntitlement, BillingOverview, CustomerAccountOverview, CustomerSubscription, Project } from "../lib/types";
import { EventCard } from "./EventCard";
import { ProjectOnboardingForm } from "./ProjectOnboardingForm";
import { StateBlock } from "./StateBlock";

type DashboardData = {
  accounts: CustomerAccountOverview[];
  billing: BillingOverview;
  projects: Project[];
};

function activeAccount(accounts: CustomerAccountOverview[]) {
  return accounts.find((account) => account.membership.status === "ACTIVE") ?? accounts[0] ?? null;
}

function visibleEntitlements(entitlements: AccountEntitlement[]) {
  return sortEntitlementKeys(entitlements).filter((entitlement) => {
    if (entitlement.status !== "ACTIVE") return false;
    return ["events", "guests_per_event", "collaborators_per_event", "committee_members_per_event", "vendors_per_event", "invitation_emails_per_month"].includes(entitlement.key);
  });
}

function subscriptionTone(subscription: CustomerSubscription | null) {
  if (!subscription) return "attention";
  if (subscription.status === "ACTIVE") return "success";
  if (["INCOMPLETE", "PAST_DUE", "FAILED"].includes(subscription.status)) return "attention";
  return "muted";
}

export function CustomerDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [status, setStatus] = useState<"anonymous" | "loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const user = getSessionUser();

  const loadDashboard = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setData(null);
      setStatus("anonymous");
      return;
    }

    setStatus("loading");
    try {
      const [accounts, billing, projects] = await Promise.all([
        apiGet<CustomerAccountOverview[]>("/customer-accounts", token),
        apiGet<BillingOverview>("/billing/subscription", token),
        apiGet<Project[]>("/projects", token)
      ]);
      cacheProjects(projects);
      setData({ accounts, billing, projects });
      setStatus("ready");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setData(null);
        setStatus("anonymous");
        return;
      }
      setMessage(error instanceof Error ? error.message : "Could not load your Ellenor Events dashboard.");
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
    return subscribeToAuthChanges(() => void loadDashboard());
  }, [loadDashboard]);

  const account = useMemo(() => activeAccount(data?.accounts ?? []), [data?.accounts]);
  const subscription = activeSubscription(data?.billing.subscriptions ?? []);
  const eventsEntitlement = account?.entitlements.find((entitlement) => entitlement.key === "events" && entitlement.status === "ACTIVE") ?? null;
  const entitlementHighlights = visibleEntitlements(account?.entitlements ?? []);
  const activeEventCount = data?.projects.filter((project) => project.status !== "archived").length ?? 0;
  const tone = subscriptionTone(subscription);

  if (status === "anonymous") {
    return (
      <>
        <section className="hero">
          <p className="eyebrow">Ellenor Events</p>
          <h1>A calm command center for ceremonies with many moving parts.</h1>
          <p>Coordinate weddings, introductions, committees, meetings, RSVP flows, contributions, and budget visibility without exposing sensitive details to people outside the event.</p>
          <div className="buttonRow">
            <Link className="primaryButton" href="/login">Sign in</Link>
            <Link className="secondaryButton" href="/packages">View packages</Link>
          </div>
        </section>
        <section className="grid twoColumns">
          <StateBlock title="Sign in to view your events" message="Your customer account, events, billing, and planning details stay private until you sign in." />
          <StateBlock title="Choose a package when ready" message="Packages show the planning capacity available for an Ellenor Events account." />
        </section>
      </>
    );
  }

  if (status === "loading") {
    return <StateBlock title="Loading your dashboard" message="Preparing your customer account, events, package, and planning access." />;
  }

  if (status === "error") {
    return <StateBlock title="Dashboard unavailable" message={message} />;
  }

  return (
    <section className="stack dashboardStack">
      <section className="hero compact customerHero">
        <div>
          <p className="eyebrow">Customer dashboard</p>
          <h1>{account ? account.account.name : "Your Ellenor Events workspace"}</h1>
          <p>
            Signed in as {user?.email ?? user?.name ?? "your Ellenor Events account"}.
            {account ? ` Account status: ${customerStatusLabel(account.account.status)} · role: ${account.membership.role.toLowerCase()}.` : ""}
          </p>
        </div>
        <div className={`summaryPill ${tone}`}>
          <span>{subscription?.status === "ACTIVE" ? "Active package" : "Access state"}</span>
          <strong>{subscription?.package_name ?? "No active package"}</strong>
        </div>
      </section>

      <section className="grid threeColumns">
        <article className="panel dashboardCard">
          <p className="eyebrow">Subscription</p>
          <h2>{subscription?.package_name ?? "No active package yet"}</h2>
          {subscription ? (
            <>
              <p className="statusLine">Status: <strong>{customerStatusLabel(subscription.status)}</strong></p>
              <p>{formatAmount(subscription.amount_minor, subscription.currency)} / {formatBillingInterval(subscription.billing_interval)}</p>
              <p>{subscription.current_period_end ? `Renews or expires on ${formatDate(subscription.current_period_end)}` : "Access period is not set yet."}</p>
              {subscription.status !== "ACTIVE" ? <p className="helperText">Your event data is preserved. Choose an active package when you are ready to continue planning.</p> : null}
            </>
          ) : (
            <p className="helperText">Choose an Ellenor Events package to activate event creation and planning access.</p>
          )}
          <div className="buttonRow compactButtons">
            <Link className="ghostButton" href="/billing">View billing</Link>
            {subscription?.status !== "ACTIVE" ? <Link className="primaryButton" href="/packages">View packages</Link> : null}
          </div>
        </article>

        <article className="panel dashboardCard">
          <p className="eyebrow">Events</p>
          <h2>{activeEventCount} active event{activeEventCount === 1 ? "" : "s"}</h2>
          <p>{eventsEntitlement ? `Events: ${entitlementQuantity(eventsEntitlement)}` : "Event access is not active yet."}</p>
          <p className="helperText">Existing event history is preserved even when package access changes.</p>
          <Link className="ghostButton eventDetailsLink" href="#events">Review events</Link>
        </article>

        <article className="panel dashboardCard">
          <p className="eyebrow">Planning attention</p>
          <h2>What needs attention</h2>
          {data?.projects.length ? (
            <p>Your event workspace is ready. Open the event to manage budget, meetings, committee, vendors, and invites according to your role.</p>
          ) : (
            <p>No event workspace exists yet. Create one when your package allows event access.</p>
          )}
          <p className="helperText">No fabricated metrics are shown; deeper planning insights will appear when the underlying activity data exists.</p>
        </article>
      </section>

      <section className="grid twoColumns" id="events">
        <article className="panel actionPanel">
          <div className="sectionHeader">
            <div>
              <p className="eyebrow">My Events</p>
              <h2>Event workspaces</h2>
            </div>
            <span className="badge">{data?.projects.length ?? 0} connected</span>
          </div>
          {data?.projects.length ? (
            <div className="stack">
              {data.projects.map((event) => (
                <EventCard key={event.id} id={event.id} title={event.title} role={event.role ?? "Member"} type={event.type} date={event.event_date ? formatDate(event.event_date) : "Date to be confirmed"} status={event.status} onOpen={() => setActiveProjectId(event.id)} />
              ))}
            </div>
          ) : (
            <div className="stack">
              <StateBlock title="No event yet" message="Start your first event workspace when your account has active event access." />
              <ProjectOnboardingForm onCreated={() => void loadDashboard()} />
            </div>
          )}
          {data?.projects.length ? (
            <details className="inlineDisclosure">
              <summary>Start another event</summary>
              <ProjectOnboardingForm onCreated={() => void loadDashboard()} />
            </details>
          ) : null}
        </article>

        <aside className="panel">
          <p className="eyebrow">Account usage</p>
          <h2>{account?.account.name ?? "Customer account"}</h2>
          {entitlementHighlights.length ? (
            <div className="usageList">
              {entitlementHighlights.map((entitlement) => (
                <div className="usageRow" key={entitlement.id}>
                  <span>{entitlementName(entitlement.key)}</span>
                  <strong>{entitlementQuantity(entitlement)}</strong>
                </div>
              ))}
            </div>
          ) : (
            <p className="helperText">No active usage limits are available yet. Choose a package to activate access.</p>
          )}
          <Link className="ghostButton eventDetailsLink" href="/billing">See subscription details</Link>
        </aside>
      </section>
    </section>
  );
}
