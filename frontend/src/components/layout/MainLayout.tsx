// import Navbar from "../Navbar";
import Footer from "../Footer";
import NewNavbar from "../NewNavbar";

function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* <Navbar /> */}
      <NewNavbar />
      <main>{children}</main>
      <Footer />
    </>
  );
}

export default MainLayout;
