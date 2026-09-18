import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Nav from "@/components/nav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ClinSynth — Clinical Research Twin Engine",
  description: "From scarce patient data to research-ready synthetic cohorts. Privacy-screened, clinically validated, subgroup-faithful.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="flex min-h-screen">
        <Nav />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">{children}</main>
      </body>
    </html>
  );
}
