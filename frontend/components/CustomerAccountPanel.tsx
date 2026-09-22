"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet } from "../lib/api";
import { getAccessToken, subscribeToAuthChanges } from "../lib/session";
import type { CustomerAccountOverview } from "../lib/types";
import { StateBlock } from "./StateBlock";

function entitlementLabel(overview: CustomerAccountOverview) {
  const eventsEntitlement = overview.entitlements.find((entitlement) => entitlement.key === "events");
  if (!eventsEntitlement) return "Event access is being prepared.";
  const limit = eventsEntitlement.quantity == null ? "available" : `${eventsEntitlement.used_quantity}/${eventsEntitlement.quantity} used`;
  return `Events: ${limit} · ${eventsEntitlement.status.toLowerCase()}`;
}

export function CustomerAccountPanel() {
  const [accounts, setAccounts] = useState<CustomerAccountOverview[]>([]);
  const [status, setStatus] = useState<"anonymous" | "loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");

  const loadAccounts = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setAccounts([]);
      setStatus("anonymous");
      return;
    }
    setStatus("loading");
    try {
      const nextAccounts = await apiGet<CustomerAccountOverview[]>("/customer-accounts", token);
      setAccounts(nextAccounts);
      setStatus("ready");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setAccounts([]);
        setStatus("anonymous");
        return;
      }
      setMessage(error instanceof Error ? error.message : "Could not load your customer account.");
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void loadAccounts();
    return subscribeToAuthChanges(() => void loadAccounts());
  }, [loadAccounts]);

  if (status === "anonymous") {
    return <StateBlock title="Customer account" message="Sign in to see your Ellenor Events account." />;
  }
  if (status === "loading") {
    return <StateBlock title="Customer account" message="Preparing your account details." />;
  }
  if (status === "error") {
    return <StateBlock title="Customer account unavailable" message={message} />;
  }
  if (!accounts.length) {
    return <StateBlock title="Customer account" message="Create your first event to activate an Ellenor Events customer account." />;
  }

  const primary = accounts[0];
  return (
    <aside className="panel">
      <p className="eyebrow">Customer Account</p>
      <h2>{primary.account.name}</h2>
      <p>Account status: {primary.account.status.toLowerCase()}</p>
      <p>Your account role: {primary.membership.role.toLowerCase()}</p>
      <p>{entitlementLabel(primary)}</p>
      <p>{primary.projects.length} event workspace{primary.projects.length === 1 ? "" : "s"} connected to this account.</p>
    </aside>
  );
}
