import { Menu, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { NAV_LINKS } from "@/constants/nav";
import logo from "@/assets/logo.svg";
import { ModeToggle } from "./shared/mode-toggle";

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  const closeMenu = () => {
    setIsOpen(false);
  };

  return (
    <nav className="sticky top-0 z-50 py-3 backdrop-blur-lg border-b border-border/60 bg-background/80">
      <div className="container px-4 mx-auto relative text-sm">
        <div className="flex justify-between items-center">
          {/* Logo */}
          <div className="flex items-center flex-shrink-0">
            <img src={logo} alt="Prime Logo" className="h-10 w-10 mr-2" />
            <span className="text-xl tracking-tight font-semibold text-primary">
              Prime
            </span>
          </div>

          {/* Desktop Navigation */}
          <ul className="hidden lg:flex ml-14 space-x-10">
            {NAV_LINKS.map((item, index) => (
              <li key={index}>
                <Link to={item.path}>
                  <p className="text-slate-700 dark:text-slate-300 hover:text-primary transition-colors duration-200 font-medium">
                    {item.label}
                  </p>
                </Link>
              </li>
            ))}
          </ul>

          {/* Desktop Actions */}
          <div className="hidden lg:flex justify-center space-x-4 items-center">
            <ModeToggle />
            <Link to="/login">
              <Button
                variant="outline"
                className="border-border hover:bg-accent hover:text-accent-foreground"
              >
                Login
              </Button>
            </Link>
            <Link to="/sign-up">
              <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                Sign Up
              </Button>
            </Link>
          </div>

          {/* Mobile Menu Toggle */}
          <div className="lg:hidden">
            <button
              onClick={toggleMenu}
              className="p-2 hover:bg-accent hover:text-accent-foreground rounded-md transition-colors duration-200"
              aria-label="Toggle menu"
            >
              {isOpen ? (
                <X size={24} className="text-foreground" />
              ) : (
                <Menu size={24} className="text-foreground" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
              onClick={closeMenu}
            />

            {/* Mobile Menu Panel */}
            <div className="fixed top-0 right-0 h-full w-80 max-w-[90vw] bg-card z-50 transform transition-transform duration-300 ease-in-out lg:hidden border-l border-border shadow-2xl">
              {/* Mobile Menu Header */}
              <div className="flex justify-between items-center p-4 border-b border-border">
                <div className="flex items-center">
                  <img src={logo} alt="Prime Logo" className="h-8 w-8 mr-2" />
                  <span className="text-lg font-semibold text-card-foreground">
                    Prime
                  </span>
                </div>
                <button
                  onClick={closeMenu}
                  className="p-2 hover:bg-accent hover:text-accent-foreground rounded-md transition-colors duration-200"
                  aria-label="Close menu"
                >
                  <X size={20} className="text-card-foreground" />
                </button>
              </div>

              {/* Mobile Navigation Links */}
              <div className="py-6">
                <ul className="space-y-1">
                  {NAV_LINKS.map((item, index) => (
                    <li key={index}>
                      <Link
                        to={item.path}
                        onClick={closeMenu}
                        className="block px-6 py-3 text-slate-700 dark:text-slate-300 hover:bg-accent hover:text-accent-foreground transition-all duration-200 font-medium"
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>

                {/* Mobile Actions */}
                <div className="px-6 mt-8 space-y-4">
                  <div className="flex justify-center">
                    <ModeToggle />
                  </div>
                  <div className="space-y-3">
                    <Link to="/login" onClick={closeMenu} className="block">
                      <Button
                        variant="outline"
                        className="w-full border-border hover:bg-accent hover:text-accent-foreground"
                      >
                        Login
                      </Button>
                    </Link>
                    <Link to="/sign-up" onClick={closeMenu} className="block">
                      <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90">
                        Sign Up
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
