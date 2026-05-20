"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/analyze", label: "Analyse" },
  { href: "/trades", label: "Trades" },
  { href: "/performance", label: "Performance" },
  { href: "/screener", label: "Screener" },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-0 flex items-center gap-1 shadow-sm sticky top-0 z-50">
      <Link href="/" className="font-extrabold text-gray-900 text-base mr-4 py-4 flex items-center gap-2">
        <span className="text-blue-600">▲</span> AI Hedge Fund
      </Link>
      {links.map(({ href, label }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={`text-sm font-medium px-3 py-4 border-b-2 transition-colors ${
              active
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-900 hover:border-gray-300"
            }`}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
