import { LoginForm } from "../../components/LoginForm";
import { PortalShell } from "../../components/PortalShell";

export default function LoginPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Welcome Back</p>
        <h1>Sign in to your Ellenor Events account.</h1>
        <p>Continue planning your events, managing the workspaces you belong to, or responding to an invitation.</p>
      </section>
      <LoginForm />
    </PortalShell>
  );
}
