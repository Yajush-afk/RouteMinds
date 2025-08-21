// import Navbar from "../Navbar";
import NewNavbar from "../NewNavbar";

function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* <Navbar /> */}
      <NewNavbar />
      <main>{children}</main>
    </>
  );
}

export default MainLayout;
