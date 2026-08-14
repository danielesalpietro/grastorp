import { NavLink } from "react-router-dom";

const linkClass = ({ isActive }: { isActive: boolean }) => "sidebar__link" + (isActive ? " active" : "");

export function Sidebar() {
  return (
    <div className="sidebar">
      <div className="sidebar__section">
        <div className="sidebar__label">Navigator</div>
        <NavLink to="/deployments" className={linkClass}>
          Deployments
        </NavLink>
        <NavLink to="/storage" className={linkClass}>
          Storage
        </NavLink>
        <NavLink to="/networking" className={linkClass}>
          Networking
        </NavLink>
        <NavLink to="/monitor" className={linkClass}>
          Monitor
        </NavLink>
      </div>
    </div>
  );
}
