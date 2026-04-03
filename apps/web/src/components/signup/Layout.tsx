import ImageSection from "@/components/signup/ImageSection"

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">

      <div className="hidden md:block w-[60%] relative h-screen sticky top-0">
        <ImageSection />
      </div>
    
      <div className="w-full md:w-[40%] flex items-center justify-center min-h-screen bg-white">
        {children}
      </div>
    </div>
  )
}