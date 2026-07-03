import { LoginForm } from "../../components/LoginForm";
import { PortalShell } from "../../components/PortalShell";

export default function LoginPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Passwordless Login</p>
        <h1>Phone-first access for families, partners, and committees.</h1>
        <p>Request an OTP by phone or use email fallback while Supabase Auth is connected.</p>
      </section>
      <LoginForm />
    </PortalShell>
  );
}
