export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-[60%_40%]">
      {children}
    </div>
  )
}