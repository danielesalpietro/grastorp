import { NavLink } from "react-router-dom";

const linkClass = ({ isActive }: { isActive: boolean }) => "sidebar__link" + (isActive ? " active" : "");
const subLinkClass = ({ isActive }: { isActive: boolean }) =>
  "sidebar__link sidebar__link--sub" + (isActive ? " active" : "");

export function Sidebar() {
  return (
    <div className="sidebar">
      <div className="sidebar__section">
        <div className="sidebar__label">Navigator</div>

        <div className="sidebar__group-header">Host</div>
        <NavLink to="/host/manage" className={subLinkClass}>
          Manage
        </NavLink>
        <NavLink to="/host/monitor" className={subLinkClass}>
          Monitor
        </NavLink>

        <NavLink to="/deployments" className={linkClass}>
          Deployments
        </NavLink>
        <NavLink to="/storage" className={linkClass}>
          Storage
        </NavLink>
        <NavLink to="/networking" className={linkClass}>
          Networking
        </NavLink>
        <NavLink to="/gpu" className={linkClass}>
          GPU
        </NavLink>
        <NavLink to="/templates" className={linkClass}>
          Templates
        </NavLink>
      </div>
    </div>
  );
}
