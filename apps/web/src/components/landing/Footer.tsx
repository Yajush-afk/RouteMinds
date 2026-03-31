export default function Footer() {
  return (
    <footer
      style={{ fontFamily: "'Syne', sans-serif" }}
      className="bg-white border-t border-gray-200 px-8 md:px-16 lg:px-24 py-6 flex items-center justify-between"
    >
      <span className="text-[#1a1a1a] font-bold text-sm">RouteMinds</span>
      <span className="text-gray-400 text-xs font-light">
        © 2026 OpenMinds. All rights reserved.
      </span>
    </footer>
  )
}