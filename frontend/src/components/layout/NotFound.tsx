import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import Navbar from "./Navbar";

export default function NotFoundPage() {
  return (
    <>
      <Navbar />
      <div className="flex flex-col items-center mt-6 lg:mt-20">
        <h1 className="text-4xl sm:text-6xl lg:text-7xl text-center tracking-wide">
          404 Not Found
        </h1>
        <p className="mt-10 text-lg text-center text-neutral-500 max-w-4xl">
          The page you are looking for does not exist.
        </p>
        <div className="flex justify-center my-10">
          <Link to={"/"}>
            <Button>Go to Home</Button>
          </Link>
        </div>
      </div>
    </>
  );
}
