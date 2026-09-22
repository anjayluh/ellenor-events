"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
import type { CatalogPackage, CheckoutResponse, PackageEntitlementGrant, PackagePrice } from "../lib/types";
import { StateBlock } from "./StateBlock";

const featureLabels: Record<string, string> = {
  budget_management: "Budget planning",
  rsvp_management: "Guest RSVP tools",
  vendor_management: "Vendor coordination",
  meeting_management: "Meeting coordination",
  task_management: "Task tracking"
};

const limitLabels: Record<string, string> = {
  events: "event workspace",
  guests_per_event: "guests per event",
  collaborators_per_event: "collaborators per event",
  vendors_per_event: "vendors per event"
};

function formatPrice(price: PackagePrice) {
  const amount = new Intl.NumberFormat("en-UG", { style: "currency", currency: price.currency, maximumFractionDigits: 0 }).format(price.amount_minor);
  const interval = price.billing_interval === "ONE_TIME" ? "one-time" : price.billing_interval.toLowerCase();
  return `${amount} · ${interval}`;
}

function describeGrant(grant: PackageEntitlementGrant) {
  if (grant.value_type === "BOOLEAN") return featureLabels[grant.entitlement_key] ?? grant.entitlement_key.replaceAll("_", " ");
  if (grant.value_type === "UNLIMITED") return `Unlimited ${limitLabels[grant.entitlement_key] ?? grant.entitlement_key.replaceAll("_", " ")}`;
  const label = limitLabels[grant.entitlement_key] ?? grant.entitlement_key.replaceAll("_", " ");
  return `${grant.quantity} ${label}`;
}

export function PackageCatalogPage() {
  const [packages, setPackages] = useState<CatalogPackage[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [checkoutStatus, setCheckoutStatus] = useState<Record<string, string>>({});

  useEffect(() => {
    void apiGet<CatalogPackage[]>("/catalog/packages")
      .then((nextPackages) => {
        setPackages(nextPackages);
        setStatus("ready");
      })
      .catch((error) => {
        setMessage(error instanceof Error ? error.message : "Could not load packages.");
        setStatus("error");
      });
  }, []);

  if (status === "loading") return <StateBlock title="Loading packages" message="Preparing Ellenor Events package options." />;
  if (status === "error") return <StateBlock title="Packages unavailable" message={message} />;
  if (!packages.length) return <StateBlock title="Packages coming soon" message="Ellenor Events packages are being prepared." />;

  async function startCheckout(price: PackagePrice) {
    setCheckoutStatus((current) => ({ ...current, [price.id]: "Preparing checkout..." }));
    try {
      const response = await apiPost<CheckoutResponse, { package_price_id: string }>("/billing/checkout", { package_price_id: price.id });
      setCheckoutStatus((current) => ({ ...current, [price.id]: "Redirecting to payment..." }));
      window.location.href = response.checkout_url;
    } catch (error) {
      setCheckoutStatus((current) => ({ ...current, [price.id]: error instanceof Error ? error.message : "Checkout is not available yet." }));
    }
  }

  return (
    <section className="stack">
      <section className="hero compact">
        <p className="eyebrow">Packages</p>
        <h1>Choose the planning support that fits your event.</h1>
        <p>These package definitions show what Ellenor Events can support. Checkout and online payment will be added in a later phase.</p>
      </section>
      <section className="grid threeColumns">
        {packages.map((catalogPackage) => (
          <article className="panel resourceCard" key={catalogPackage.id}>
            <p className="eyebrow">{catalogPackage.is_add_on ? "Add-on" : "Package"}</p>
            <h2>{catalogPackage.name}</h2>
            <p>{catalogPackage.description}</p>
            <div className="meta">
              {catalogPackage.prices.length ? catalogPackage.prices.map((price) => <span className="badge" key={price.id}>{formatPrice(price)}</span>) : <span className="badge">Pricing to be confirmed</span>}
            </div>
            <ul>
              {catalogPackage.entitlement_grants.map((grant) => <li key={grant.id}>{describeGrant(grant)}</li>)}
            </ul>
            <div className="buttonRow compactButtons">
              {catalogPackage.prices.length ? catalogPackage.prices.map((price) => (
                <button className="primaryButton" data-icon="→" disabled={checkoutStatus[price.id] === "Preparing checkout..." || checkoutStatus[price.id] === "Redirecting to payment..."} key={price.id} type="button" onClick={() => void startCheckout(price)}>
                  {checkoutStatus[price.id] === "Preparing checkout..." ? "Preparing..." : "Choose package"}
                </button>
              )) : <button className="ghostButton" disabled type="button">Checkout coming soon</button>}
            </div>
            {catalogPackage.prices.map((price) => checkoutStatus[price.id] ? <p className="helperText" key={`${price.id}-status`}>{checkoutStatus[price.id]}</p> : null)}
          </article>
        ))}
      </section>
    </section>
  );
}
