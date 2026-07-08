import type { Metadata, Viewport } from "next";
import "./globals.css";
import RegisterSW from "@/components/pwa/RegisterSW";

export const metadata: Metadata = {
  title: "Kundali — Vedic Astrology Engine",
  description:
    "Deterministic jyotisha: South Indian charts, shodasha vargas, Vimshottari dashas, gochara, yogas and grounded predictions.",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Kundali",
  },
  icons: {
    apple: "/icons/icon-192.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#0b0e1d",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {children}
        <RegisterSW />
      </body>
    </html>
  );
}
