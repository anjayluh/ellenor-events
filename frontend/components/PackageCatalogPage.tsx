"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
import { activeSubscription, customerStatusLabel, describeGrant, formatPrice } from "../lib/customer-display";
import { getAccessToken, subscribeToAuthChanges } from "../lib/session";
import type { BillingOverview, CatalogPackage, CheckoutResponse, PackagePrice } from "../lib/types";
import { StateBlock } from "./StateBlock";

export function PackageCatalogPage() {
  const [packages, setPackages] = useState<CatalogPackage[]>([]);
  const [billing, setBilling] = useState<BillingOverview | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [checkoutStatus, setCheckoutStatus] = useState<Record<string, string>>({});

  useEffect(() => {
    const loadCatalog = async () => {
      try {
        const nextPackages = await apiGet<CatalogPackage[]>("/catalog/packages");
        setPackages(nextPackages);
        const token = getAccessToken();
        if (token) {
          try {
            setBilling(await apiGet<BillingOverview>("/billing/subscription", token));
          } catch {
            setBilling(null);
          }
        } else {
          setBilling(null);
        }
        setStatus("ready");
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Could not load packages.");
        setStatus("error");
      }
    };

    void loadCatalog();
    return subscribeToAuthChanges(() => void loadCatalog());
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

  const currentSubscription = activeSubscription(billing?.subscriptions ?? []);
  const activePackagePriceId = currentSubscription?.status === "ACTIVE" ? currentSubscription.package_price_id : null;
  const activePackagePlanId = currentSubscription?.status === "ACTIVE" ? currentSubscription.package_plan_id : null;
  const isAuthenticated = Boolean(getAccessToken());

  return (
    <section className="stack">
      <section className="hero compact">
        <p className="eyebrow">Packages</p>
        <h1>Choose the planning support that fits your event.</h1>
        <p>Packages define the event capacity and planning tools available to your Ellenor Events account. Checkout always uses the package price selected from the backend catalog.</p>
      </section>
      <section className="grid threeColumns">
        {packages.map((catalogPackage) => (
          <article className="panel resourceCard" key={catalogPackage.id}>
            <p className="eyebrow">{catalogPackage.is_add_on ? "Add-on" : "Package"}</p>
            <div className="cardTitleRow">
              <h2>{catalogPackage.name}</h2>
              {activePackagePlanId === catalogPackage.id ? <span className="badge successBadge">Current package</span> : null}
            </div>
            <p>{catalogPackage.description}</p>
            <div className="meta">
              {catalogPackage.prices.length ? catalogPackage.prices.map((price) => <span className="badge" key={price.id}>{formatPrice(price)}</span>) : <span className="badge">Pricing to be confirmed</span>}
            </div>
            <ul>
              {catalogPackage.entitlement_grants.map((grant) => <li key={grant.id}>{describeGrant(grant)}</li>)}
            </ul>
            <div className="buttonRow compactButtons">
              {!isAuthenticated && catalogPackage.prices.length ? (
                <Link className="primaryButton" href="/login">Sign in to choose</Link>
              ) : catalogPackage.prices.length ? catalogPackage.prices.map((price) => (
                <button className={activePackagePriceId === price.id ? "ghostButton" : "primaryButton"} data-icon={activePackagePriceId === price.id ? "✓" : "→"} disabled={activePackagePriceId === price.id || checkoutStatus[price.id] === "Preparing checkout..." || checkoutStatus[price.id] === "Redirecting to payment..."} key={price.id} type="button" onClick={() => void startCheckout(price)}>
                  {activePackagePriceId === price.id ? "Current package" : checkoutStatus[price.id] === "Preparing checkout..." ? "Preparing..." : "Choose package"}
                </button>
              )) : <button className="ghostButton" disabled type="button">Checkout coming soon</button>}
            </div>
            {catalogPackage.prices.map((price) => checkoutStatus[price.id] ? <p className="helperText" key={`${price.id}-status`}>{checkoutStatus[price.id]}</p> : null)}
            {currentSubscription && activePackagePlanId === catalogPackage.id ? <p className="helperText">Your current access is {customerStatusLabel(currentSubscription.status)}.</p> : null}
          </article>
        ))}
      </section>
    </section>
  );
}
