import { Menu, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { NAV_LINKS } from "@/constants/nav";
import logo from "@/assets/logo.svg";
import ThemeToggle from "../shared/ThemeSwitch";

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  return (
    <>
      <nav className="sticky top-0 z-50 py-3 backdrop-blur-lg border-b border-neutral-700/80">
        <div className="container px-4 mx-auto relative text-sm">
          <div className="flex justify-between items-center">
            <div className="flex items-center flex-shrink-0">
              <img src={logo} alt="logo" className="h-10 w-10 mr-2" />
              <span className="text-xl tracking-tight">Prime</span>
            </div>
            <ul className="hidden lg:flex ml-14 space-x-10">
              {NAV_LINKS.map((item, index) => (
                <li key={index}>
                  <Link to={item.path}>{item.label}</Link>
                </li>
              ))}
            </ul>
            <div className="hidden lg:flex justify-center space-x-4 items-center">
              <ThemeToggle />
              <Link to={"/login"}>
                <Button variant="outline">Login</Button>
              </Link>
              <Link to={"/sign-up"}>
                <Button>Sign Up</Button>
              </Link>
            </div>
            <div className="lg:hidden md:flex flex-col justify-end">
              <button onClick={toggleMenu}>{isOpen ? <X /> : <Menu />}</button>
            </div>
          </div>
          {isOpen && (
            <div className="fixed right-0 z-20 bg-neutral-900 w-full py-8 flex flex-col justify-center items-center gap-4 lg:hidden">
              <ul>
                {NAV_LINKS.map((item, index) => (
                  <li key={index} className="py-4">
                    <Link to={item.path}>{item.label}</Link>
                  </li>
                ))}
              </ul>
              <div className="flex gap-4 space-y-2">
                <Button variant="outline">Sign In</Button>
                <Button>Sign Up</Button>
              </div>
            </div>
          )}
        </div>
      </nav>
    </>
  );
};

export default Navbar;
