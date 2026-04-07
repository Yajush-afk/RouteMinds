export default function Footer() {
  const team = [
    { handle: "@Yajush_who", href: "https://x.com/Yajush_who" },
    { handle: "@fuzzykny", href: "https://x.com/fuzzykny" },
    { handle: "@MaheshGoya77594", href: "https://x.com/MaheshGoya77594" },
    { handle: "@iamtanuuuu", href: "https://x.com/iamtanuuuu" },
  ]

  return (
    <footer
      className=" pt-20 px-4 pb-10 sm:px-6 md:px-10 lg:px-24"
      style={{ background: "linear-gradient(to bottom, #ffffff, #e2e8f0)" }}
    >
      

      <div className="mx-auto max-w-7xl flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between px-6 md:px-16 lg:px-24">

        <div>
          <p className="font-heading text-xl text-foreground mb-2">RouteMinds</p>
          <p className="font-body text-sm text-muted-foreground max-w-xs leading-relaxed">
            AI-powered delay predictions for Delhi's transit network.
          </p>
        </div>

        <div>
          <p className="font-body text-xs font-semibold tracking-widest text-muted-foreground uppercase mb-4">
            Created by
          </p>
          <ul className="flex flex-col gap-3">
            {team.map((member) => (
              <li key={member.handle} className="flex items-center gap-2">
                <svg
                  viewBox="0 0 24 24"
                  className="h-3.5 w-3.5 shrink-0 fill-current text-foreground/50"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.73-8.835L1.254 2.25H8.08l4.253 5.622 5.912-5.622Zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
                <a
                  href={member.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-body text-sm text-foreground/70 transition-colors hover:text-foreground"
                >
                  {member.handle}
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mx-auto max-w-7xl mt-12 pt-6 border-t border-gray-400">
        <p className="font-body text-xs text-muted-foreground">
          © 2026 RouteMinds. All rights reserved.
        </p>
      </div>
    </footer>
  )
}