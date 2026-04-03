import { Button } from "@workspace/ui/components/button"
import { Input } from "@workspace/ui/components/input"
import { Label } from "@workspace/ui/components/label"
import { Separator } from "@workspace/ui/components/separator"

export default function RightSection() {
  return (
    <div className="flex flex-col justify-center px-12 py-16 bg-white"
      style={{ fontFamily: "'Poppins', sans-serif" }}
    >
      <div className="max-w-sm w-full mx-auto">

        <h1 className="text-3xl font-medium text-[#1a1a1a] mb-2">
          Login your account
        </h1>
        <p className="text-[#555] text-sm mb-8">
          Let's get started with RouteMinds.
        </p>

        <div className="space-y-5">

          <div className="space-y-1.5">
            <Label htmlFor="email" className="text-sm font-medium text-[#1a1a1a]">
              Email
            </Label>
            <Input
             id="email"
             type="email"
             placeholder="Enter your email"
             className= " w-full px-3 py-2 rounded-md !border !border-gray-300 bg-white text-gray-900 placeholder:text-gray-400 hover:!border-gray-400 focus:!border-gray-900 focus:!ring-1 focus:!ring-gray-900/20 focus:!outline-none transition-all duration-150"/>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password" className="text-sm font-medium text-[#1a1a1a]">
              Password
            </Label>
            <Input
              id="password"
              type="password"
              placeholder="Create a password"
             className= " w-full px-3 py-2 rounded-md !border !border-gray-300 bg-white text-gray-900 placeholder:text-gray-400 hover:!border-gray-400 focus:!border-gray-900 focus:!ring-1 focus:!ring-gray-900/20 focus:!outline-none transition-all duration-150"/>
          </div>

          
          <Button
            className="w-full bg-[#1a1a1a] text-white hover:bg-[#333] transition-colors shadow-xl/20"
          >
            Login
          </Button>

          <div className="flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs text-gray-400">or</span>
            <Separator className="flex-1" />
          </div>

          <Button
  variant="outline"
  className="w-full !border !border-black !text-black hover:!bg-black hover:!text-white transition-colors flex items-center gap-2 shadow-xl/20"
>
            <svg width="18" height="18" viewBox="0 0 18 18">
              <path fill="#4285F4" d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z"/>
              <path fill="#34A853" d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17z"/>
              <path fill="#FBBC05" d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18z"/>
              <path fill="#EA4335" d="M8.98 4.18c1.17 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.3z"/>
            </svg>
            Login with Google
          </Button>

        </div>

      </div>
    </div>
  )
}