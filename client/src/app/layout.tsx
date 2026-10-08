import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "AgentPay Nexus | Commerce orchestration",
  description: "A portfolio workspace for controlled purchasing, merchant pricing, human approvals, and auditable commerce workflows.",
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <a href="#workspace" className="skip-link">Skip to workspace</a>
        {children}
      </body>
    </html>
  );
}
