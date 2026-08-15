import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Deployments } from "./pages/Deployments";
import { DeployWizard } from "./pages/DeployWizard";
import { ModelConfiguration } from "./pages/ModelConfiguration";
import { Storage } from "./pages/Storage";
import { Networking } from "./pages/Networking";
import { Security } from "./pages/Security";
import { Gpu } from "./pages/Gpu";
import { HostManage } from "./pages/host/HostManage";
import { HostMonitor } from "./pages/host/HostMonitor";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/host/manage" replace />} />
        <Route path="/host/manage" element={<HostManage />} />
        <Route path="/host/monitor" element={<HostMonitor />} />
        <Route path="/deployments" element={<Deployments />} />
        <Route path="/deployments/new" element={<DeployWizard />} />
        <Route path="/deployments/:id" element={<ModelConfiguration />} />
        <Route path="/storage" element={<Storage />} />
        <Route path="/networking" element={<Networking />} />
        <Route path="/security" element={<Security />} />
        <Route path="/gpu" element={<Gpu />} />
      </Route>
    </Routes>
  );
}
