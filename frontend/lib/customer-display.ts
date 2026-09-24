import type { AccountEntitlement, CustomerSubscription, PackageEntitlementGrant, PackagePrice } from "./types";

export const entitlementLabels: Record<string, string> = {
  account_owners: "Account owners",
  budget_management: "Budget planning",
  collaborators_per_event: "Collaborators",
  committee_management: "Committee coordination",
  committee_members_per_event: "Committee members",
  documents_notes: "Documents and notes",
  event_management: "Event management",
  events: "Events",
  guests_per_event: "Guests",
  introduction_family_structure: "Introduction family structure",
  invitation_emails_per_month: "Invitation emails",
  invitations: "Invitations",
  meeting_management: "Meetings",
  payment_deposit_tracking: "Payment and deposit tracking",
  rsvp_management: "RSVP management",
  task_management: "Tasks and timeline",
  vendor_management: "Vendor coordination",
  vendors_per_event: "Vendors"
};

export const visibleEntitlementOrder = [
  "events",
  "guests_per_event",
  "collaborators_per_event",
  "committee_members_per_event",
  "vendors_per_event",
  "invitation_emails_per_month",
  "budget_management",
  "rsvp_management",
  "vendor_management",
  "meeting_management",
  "task_management",
  "committee_management",
  "invitations",
  "payment_deposit_tracking",
  "documents_notes",
  "introduction_family_structure",
  "account_owners"
];

export function formatAmount(amountMinor: number, currency: string) {
  return new Intl.NumberFormat("en-UG", { style: "currency", currency, maximumFractionDigits: 0 }).format(amountMinor);
}

export function formatBillingInterval(interval: string) {
  if (interval === "ONE_TIME") return "one-time";
  return interval.toLowerCase();
}

export function formatPrice(price: PackagePrice) {
  return `${formatAmount(price.amount_minor, price.currency)} / ${formatBillingInterval(price.billing_interval)}`;
}

export function formatDate(value?: string | null) {
  if (!value) return "Not set yet";
  return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function customerStatusLabel(status: string) {
  return status.toLowerCase().replaceAll("_", " ");
}

export function entitlementName(key: string) {
  return entitlementLabels[key] ?? key.replaceAll("_", " ");
}

export function describeGrant(grant: PackageEntitlementGrant) {
  const label = entitlementName(grant.entitlement_key);
  if (grant.value_type === "BOOLEAN") return label;
  if (grant.value_type === "UNLIMITED") return `Unlimited ${label.toLowerCase()}`;
  if (grant.entitlement_key.endsWith("_per_event")) return `Up to ${grant.quantity} ${label.toLowerCase()} per event`;
  if (grant.entitlement_key.endsWith("_per_month")) return `${grant.quantity} ${label.toLowerCase()} per month`;
  if (grant.entitlement_key === "events") return `${grant.quantity} event workspace${grant.quantity === 1 ? "" : "s"}`;
  return `${grant.quantity} ${label.toLowerCase()}`;
}

export function entitlementQuantity(entitlement: Pick<AccountEntitlement, "quantity" | "used_quantity" | "key">) {
  if (entitlement.quantity == null) return "Available";
  if (entitlement.key === "events") return `${entitlement.used_quantity}/${entitlement.quantity} used`;
  if (entitlement.key.endsWith("_per_event")) return `Up to ${entitlement.quantity} per event`;
  if (entitlement.key.endsWith("_per_month")) return `${entitlement.quantity} per month`;
  return String(entitlement.quantity);
}

export function subscriptionEntitlementQuantity(entitlement: Record<string, unknown>) {
  const key = String(entitlement.key ?? "");
  const quantity = typeof entitlement.quantity === "number" ? entitlement.quantity : null;
  const used = typeof entitlement.used_quantity === "number" ? entitlement.used_quantity : 0;
  if (quantity == null) return "Available";
  if (!key.endsWith("_per_event") && !key.endsWith("_per_month") && !["account_owners", "events"].includes(key) && quantity === 1) {
    return "Included";
  }
  return entitlementQuantity({ key, quantity, used_quantity: used });
}

export function sortEntitlementKeys<T extends { key?: string; entitlement_key?: string }>(items: T[]) {
  return [...items].sort((first, second) => {
    const firstKey = first.key ?? first.entitlement_key ?? "";
    const secondKey = second.key ?? second.entitlement_key ?? "";
    const firstIndex = visibleEntitlementOrder.indexOf(firstKey);
    const secondIndex = visibleEntitlementOrder.indexOf(secondKey);
    return (firstIndex === -1 ? 999 : firstIndex) - (secondIndex === -1 ? 999 : secondIndex);
  });
}

export function activeSubscription(subscriptions: CustomerSubscription[]) {
  return subscriptions.find((subscription) => subscription.status === "ACTIVE") ?? subscriptions[0] ?? null;
}
