import type { Metadata } from "next";
import Script from "next/script";
import { Fraunces, Instrument_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600"],
  display: "swap",
});

const instrumentSans = Instrument_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600"],
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "SaludPR — Panel de Salud de Puerto Rico",
  description:
    "Free, bilingual public health dashboard for Puerto Rico. Chronic disease, hospital capacity, and medically underserved zones by municipality. Built by Dataurea.",
  metadataBase: new URL("https://saludpr.org"),
  openGraph: {
    title: "SaludPR",
    description: "Panel de Salud pública de Puerto Rico, construido por Dataurea.",
    locale: "es_PR",
    alternateLocale: "en_US",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
<html
      lang="es"
      className={`${fraunces.variable} ${instrumentSans.variable} ${ibmPlexMono.variable}`}
    >
      {/* Umami Analytics — self-hosted, privacy-first, cookieless */}
      <Script
        defer
        src="/stats/script.js"
        data-website-id="c2e5c0fe-98c3-409b-b4eb-a206955d2fe7"
        strategy="afterInteractive"
      />
      <body>{children}</body>
    </html>
  );
}
