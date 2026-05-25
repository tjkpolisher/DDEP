import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DDEP",
  description: "Drone Diagnosis and Education Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
