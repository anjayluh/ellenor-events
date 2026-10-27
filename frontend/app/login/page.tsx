import { LoginForm } from "../../components/LoginForm";
import { PortalShell } from "../../components/PortalShell";

export default function LoginPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Welcome to Ellenor Events</p>
        <h1>Your event planning space, ready when you are.</h1>
        <p>Sign in or create an account to keep your events, people, and planning details together in one calm, private workspace.</p>
      </section>
      <LoginForm />
    </PortalShell>
  );
}
