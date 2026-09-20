import {Outlet} from "react-router-dom";
import Navbar from "../components/Navbar.jsx";

function StudentLayout() {
    return (
        <>
            <Navbar />
            <main className="bg-light min-vh-100">
                <Outlet />
            </main>
        </>
    );
}

export default StudentLayout;