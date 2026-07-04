import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kundali — Vedic Astrology Engine",
  description:
    "Deterministic jyotisha: South Indian charts, shodasha vargas, Vimshottari dashas, gochara, yogas and grounded predictions.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
