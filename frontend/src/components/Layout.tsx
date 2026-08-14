import { Outlet } from "react-router-dom";
import { TopBar } from "./TopBar";
import { Sidebar } from "./Sidebar";
import { RecentTasks } from "./RecentTasks";

export function Layout() {
  return (
    <>
      <TopBar />
      <div className="app-body">
        <Sidebar />
        <div className="main-area">
          <div className="content">
            <Outlet />
          </div>
          <RecentTasks />
        </div>
      </div>
    </>
  );
}
