import { Menu, X } from "lucide-react";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { NAV_LINKS } from "@/constants/nav";
import logo from "@/assets/logo.svg";
import { ModeToggle } from "./shared/mode-toggle";

const NewNavbar = () => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => setIsOpen((prev) => !prev);
  const closeSidebar = () => setIsOpen(false);

  // Handle escape key + body scroll
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        closeSidebar();
      }
    };

    document.addEventListener("keydown", handleEscape);
    document.body.style.overflow = isOpen ? "hidden" : "unset";

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  return (
    <>
      {/* Top Navbar */}
      <nav className="sticky top-0 z-50 py-3 backdrop-blur-lg border-b border-neutral-700/80 bg-background/80">
        <div className="container px-4 mx-auto relative text-sm">
          <div className="flex justify-between items-center">
            
            {/* Logo */}
            <div className="hidden lg:flex items-center flex-shrink-0">
              <img src={logo} alt="Prime Logo" className="h-10 w-10 mr-2" />
              <span className="text-xl tracking-tight font-semibold">Prime</span>
            </div>

            {/* Desktop nav links */}
            <ul className="hidden lg:flex ml-14 space-x-10">
              {NAV_LINKS.map((item, index) => (
                <li key={index}>
                  <Link
                    to={item.path}
                    className="text-neutral-300 hover:text-white transition-colors duration-200"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>

            {/* Desktop actions */}
            <div className="hidden lg:flex justify-center space-x-4 items-center">
              <ModeToggle />
              <Link to="/login">
                <Button variant="outline">Login</Button>
              </Link>
              <Link to="/sign-up">
                <Button>Sign Up</Button>
              </Link>
            </div>

            {/* Mobile toggle */}
            <div className="lg:hidden flex items-center">
              <button
                onClick={toggleMenu}
                className="p-2 text-neutral-300 hover:text-white transition-colors duration-200 rounded-md"
                aria-label={isOpen ? "Close menu" : "Open menu"}
              >
                {isOpen ? <X size={24} /> : <Menu size={24} />}
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Backdrop overlay */}
      <div
        className={`fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity duration-300 lg:hidden ${
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={closeSidebar}
      />

      {/* Mobile sidebar */}
      <div
        className={`fixed top-0 left-0 h-full w-80 bg-background border-r border-neutral-700/50 shadow-2xl z-50 transform transition-transform duration-300 ease-in-out lg:hidden ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Sidebar header */}
        <div className="flex items-center justify-between p-6 border-b border-neutral-700/50">
          <div className="flex items-center space-x-3">
            <img src={logo} alt="Prime Logo" className="h-10 w-10" />
            <div>
              <h2 className="text-lg font-semibold">Prime</h2>
              <p className="text-sm text-neutral-400">Navigation</p>
            </div>
          </div>
          <button
            onClick={closeSidebar}
            className="p-2 rounded-lg hover:bg-neutral-800 transition-colors duration-200"
            aria-label="Close menu"
          >
            <X size={20} className="text-neutral-400" />
          </button>
        </div>

        {/* Sidebar nav */}
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {NAV_LINKS.map((item, index) => (
              <li key={index}>
                <Link
                  to={item.path}
                  onClick={closeSidebar}
                  className="flex items-center p-3 rounded-xl hover:bg-neutral-800 transition-all duration-200 group"
                >
                  <span className="text-neutral-300 group-hover:text-white font-medium">
                    {item.label}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* Sidebar footer */}
        <div className="p-4 border-t border-neutral-700/50">
          <div className="space-y-3">
            <div className="flex justify-center">
              <ModeToggle />
            </div>
            <div className="flex flex-col space-y-2">
              <Link to="/login" onClick={closeSidebar}>
                <Button variant="outline" className="w-full">Login</Button>
              </Link>
              <Link to="/sign-up" onClick={closeSidebar}>
                <Button className="w-full">Sign Up</Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default NewNavbar;
