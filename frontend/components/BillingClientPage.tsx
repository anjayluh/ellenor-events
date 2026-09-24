"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import { activeSubscription, customerStatusLabel, entitlementName, formatAmount, formatBillingInterval, formatDate, sortEntitlementKeys, subscriptionEntitlementQuantity } from "../lib/customer-display";
import type { BillingOverview } from "../lib/types";
import { StateBlock } from "./StateBlock";

export function BillingClientPage() {
  const [overview, setOverview] = useState<BillingOverview | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    void apiGet<BillingOverview>("/billing/subscription")
      .then((nextOverview) => {
        setOverview(nextOverview);
        setStatus("ready");
      })
      .catch((error) => {
        setMessage(error instanceof Error ? error.message : "Could not load billing.");
        setStatus("error");
      });
  }, []);

  if (status === "loading") return <StateBlock title="Loading billing" message="Preparing your Ellenor Events billing status." />;
  if (status === "error") return <StateBlock title="Billing unavailable" message={message} />;
  if (!overview || !overview.subscriptions.length) return <StateBlock title="No active package yet" message="Choose a package to activate event access for your customer account." />;

  const currentSubscription = activeSubscription(overview.subscriptions);
  const visibleEntitlements = sortEntitlementKeys(currentSubscription?.entitlement_summary ?? []);

  return (
    <section className="stack">
      <section className="hero compact">
        <p className="eyebrow">Billing</p>
        <h1>Your Ellenor Events access</h1>
        <p>Review your current package, access source, renewal or expiry date, and recent payment attempts.</p>
      </section>
      <section className="grid twoColumns">
        <article className="panel dashboardCard">
          <p className="eyebrow">Current Subscription</p>
          <h2>{currentSubscription?.package_name ?? "Ellenor Events package"}</h2>
          {currentSubscription ? (
            <>
              <p className="statusLine">Status: <strong>{customerStatusLabel(currentSubscription.status)}</strong></p>
              <p>{formatAmount(currentSubscription.amount_minor, currentSubscription.currency)} / {formatBillingInterval(currentSubscription.billing_interval)}</p>
              <p>Started: {formatDate(currentSubscription.started_at ?? currentSubscription.current_period_start)}</p>
              <p>{currentSubscription.current_period_end ? `Renews or expires on ${formatDate(currentSubscription.current_period_end)}` : "Renewal or expiry date is not set yet."}</p>
              <p className="helperText">
                {currentSubscription.access_source === "MARKETING" ? "This access was granted through an Ellenor Events promotion." : "This access is connected to your selected package."}
                {currentSubscription.cancel_at_period_end ? " It is set to end at the current period close." : ""}
              </p>
            </>
          ) : (
            <p className="helperText">Choose an active package to see subscription details.</p>
          )}
        </article>

        <article className="panel dashboardCard">
          <p className="eyebrow">Entitlements</p>
          <h2>What your account can use</h2>
          {visibleEntitlements.length ? (
            <div className="usageList">
              {visibleEntitlements.map((entitlement, index) => (
                <div className="usageRow" key={`${String(entitlement.key)}-${index}`}>
                  <span>{entitlementName(String(entitlement.key))}</span>
                  <strong>{subscriptionEntitlementQuantity(entitlement)}</strong>
                </div>
              ))}
            </div>
          ) : (
            <p className="helperText">No active entitlement summary is available for this package yet.</p>
          )}
        </article>

        <article className="panel tablePanel">
          <p className="eyebrow">Other Access Records</p>
          <h2>Subscription history</h2>
          <div className="tableScroller">
            <table className="dataTable">
              <thead><tr><th>Package</th><th>Status</th><th>Amount</th><th>Period</th></tr></thead>
              <tbody>{overview.subscriptions.map((subscription) => (
                <tr key={subscription.id}>
                  <td>{subscription.package_name ?? "Ellenor Events package"}<small>{subscription.access_source === "MARKETING" ? "Promotional access" : "Package access"}</small></td>
                  <td>{customerStatusLabel(subscription.status)}</td>
                  <td>{formatAmount(subscription.amount_minor, subscription.currency)}</td>
                  <td>{subscription.current_period_end ? formatDate(subscription.current_period_end) : "Not set"}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </article>

        <section className="panel tablePanel">
          <p className="eyebrow">Payments</p>
          <h2>Recent payment attempts</h2>
          {overview.payments.length ? (
            <div className="tableScroller">
              <table className="dataTable">
                <thead><tr><th>Date</th><th>Amount</th><th>Status</th><th>Reference</th></tr></thead>
                <tbody>{overview.payments.map((payment) => (
                  <tr key={payment.id}>
                    <td>{formatDate(payment.created_at)}<small>{new Date(payment.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small></td>
                    <td>{formatAmount(payment.amount_minor, payment.currency)}</td>
                    <td>{customerStatusLabel(payment.status)}</td>
                    <td>{payment.provider}<small>{payment.provider_reference}</small></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ) : (
            <StateBlock title="No payment attempts yet" message="Payment history will appear here after checkout begins." />
          )}
        </section>
      </section>
    </section>
  );
}
