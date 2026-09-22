"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import type { BillingOverview } from "../lib/types";
import { StateBlock } from "./StateBlock";

function formatAmount(amountMinor: number, currency: string) {
  return new Intl.NumberFormat("en-UG", { style: "currency", currency, maximumFractionDigits: 0 }).format(amountMinor);
}

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
  if (!overview || !overview.subscriptions.length) return <StateBlock title="No active package yet" message="Choose a package to activate paid or marketing access for your customer account." />;

  return (
    <section className="stack">
      <section className="hero compact">
        <p className="eyebrow">Billing</p>
        <h1>Your Ellenor Events access</h1>
        <p>Review your current package, access source, renewal or expiry date, and recent payment attempts.</p>
      </section>
      <section className="grid twoColumns">
        {overview.subscriptions.map((subscription) => (
          <article className="panel" key={subscription.id}>
            <p className="eyebrow">{subscription.access_source === "MARKETING" ? "Marketing Access" : "Paid Subscription"}</p>
            <h2>{subscription.package_name ?? "Ellenor Events package"}</h2>
            <p>Status: {subscription.status.toLowerCase().replaceAll("_", " ")}</p>
            <p>{formatAmount(subscription.amount_minor, subscription.currency)} · {subscription.billing_interval.toLowerCase()}</p>
            <p>{subscription.cancel_at_period_end ? "Cancels at period end" : "Renewal/cancellation unchanged"}</p>
            <p>{subscription.current_period_end ? `Current access through ${new Date(subscription.current_period_end).toLocaleDateString()}` : "Access period not set yet"}</p>
            <ul>
              {subscription.entitlement_summary.map((entitlement, index) => <li key={`${subscription.id}-${index}`}>{String(entitlement.key)}{entitlement.quantity ? `: ${String(entitlement.quantity)}` : ""}</li>)}
            </ul>
          </article>
        ))}
      </section>
      <section className="panel tablePanel">
        <p className="eyebrow">Payments</p>
        <h2>Recent payment attempts</h2>
        <div className="tableScroller">
          <table className="dataTable">
            <thead><tr><th>Amount</th><th>Status</th><th>Provider</th><th>When</th></tr></thead>
            <tbody>{overview.payments.map((payment) => <tr key={payment.id}><td>{formatAmount(payment.amount_minor, payment.currency)}</td><td>{payment.status}</td><td>{payment.provider}</td><td>{new Date(payment.created_at).toLocaleString()}</td></tr>)}</tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
