import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Orb Sys",
  description: "Polycentric Autonomy-Audit governance platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-orbsys-void text-orbsys-text font-body antialiased">
        {children}
      </body>
    </html>
  );
}
