import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Deployments } from "./pages/Deployments";
import { DeployWizard } from "./pages/DeployWizard";
import { ModelConfiguration } from "./pages/ModelConfiguration";
import { Storage } from "./pages/Storage";
import { Networking } from "./pages/Networking";
import { Monitor } from "./pages/Monitor";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/deployments" replace />} />
        <Route path="/deployments" element={<Deployments />} />
        <Route path="/deployments/new" element={<DeployWizard />} />
        <Route path="/deployments/:id" element={<ModelConfiguration />} />
        <Route path="/storage" element={<Storage />} />
        <Route path="/networking" element={<Networking />} />
        <Route path="/monitor" element={<Monitor />} />
      </Route>
    </Routes>
  );
}
