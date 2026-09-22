import { PortalShell } from "../../components/PortalShell";
import { ResetPasswordForm } from "../../components/ResetPasswordForm";

export default function ResetPasswordPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Account Help</p>
        <h1>Choose a new Ellenor Events password.</h1>
        <p>Use the reset link from your email to update your password, then sign in again with your new details.</p>
      </section>
      <ResetPasswordForm />
    </PortalShell>
  );
}
