import "./globals.css";

export const metadata = {
  title: "MARSAR — Bitcoin Forensics & AML",
  description: "Bitcoin transaction forensics, clustering, and AML screening.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
