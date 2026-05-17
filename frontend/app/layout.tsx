import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Hedge Fund",
  description: "Multi-Agenten KI-Handelssystem",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body className={inter.className}>
        <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-6 shadow-sm sticky top-0 z-50">
          <span className="font-extrabold text-gray-900 text-lg mr-4">AI Hedge Fund</span>
          <Link href="/" className="text-sm text-gray-600 hover:text-gray-900 font-medium">Dashboard</Link>
          <Link href="/analyze" className="text-sm text-gray-600 hover:text-gray-900 font-medium">Analyse</Link>
          <Link href="/trades" className="text-sm text-gray-600 hover:text-gray-900 font-medium">Trades</Link>
          <Link href="/performance" className="text-sm text-gray-600 hover:text-gray-900 font-medium">Performance</Link>
          <Link href="/screener" className="text-sm text-gray-600 hover:text-gray-900 font-medium">Screener</Link>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
