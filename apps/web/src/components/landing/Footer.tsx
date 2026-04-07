export default function Footer() {
  return (
    <footer className=" px-4 pt-20 pb-12 min-h-[220px] sm:px-6 md:px-10 lg:px-24"
    style={{ background: "linear-gradient(to bottom, white, #fef3c7)" }}
    >
      <div className="border-t border-border mb-6" />
      <div className="pt-6 text-center">
        <span className=" font-body text-xs font-light text-muted-foreground sm:text-sm">
          © 2026 OpenMinds. All rights reserved.
        </span>
      </div>
    </footer>
  )
}