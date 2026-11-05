import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SigmaSpire | Institutional Algorithmic Trading",
  description: "Your Algorithm. Your Mantra. Your Edge.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-950 text-slate-100">{children}</body>
    </html>
  );
}
