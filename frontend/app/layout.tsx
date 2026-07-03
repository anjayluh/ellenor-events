import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Ellenor Events",
  description: "Wedding and introduction ceremony coordination platform"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
