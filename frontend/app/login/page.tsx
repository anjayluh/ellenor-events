import { LoginForm } from "../../components/LoginForm";
import { PortalShell } from "../../components/PortalShell";

export default function LoginPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Secure Login</p>
        <h1>Email and password access backed by Supabase Auth.</h1>
        <p>Personal event data, budgets, vendors, meetings, and staff tools stay hidden until your account is authenticated and authorized.</p>
      </section>
      <LoginForm />
    </PortalShell>
  );
}
