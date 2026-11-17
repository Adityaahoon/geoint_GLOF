import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import { Layout } from "./components/Layout";
import { OverviewDashboard } from "./pages/OverviewDashboard";
import { SatelliteExplorer } from "./pages/SatelliteExplorer";
import { GlacialLakeDetection } from "./pages/GlacialLakeDetection";
import { HistoricalChangeAnalysis } from "./pages/HistoricalChangeAnalysis";
import { DisasterImpactAnalysis } from "./pages/DisasterImpactAnalysis";
import { GlacierMonitoring } from "./pages/GlacierMonitoring";
import { GlofSusceptibility } from "./pages/GlofSusceptibility";
import { FloodSimulation } from "./pages/FloodSimulation";
import { InfrastructureExposure } from "./pages/InfrastructureExposure";
import { GeoTiffWorkspace } from "./pages/GeoTiffWorkspace";
import { ModelLab } from "./pages/ModelLab";
import { ReportGenerator } from "./pages/ReportGenerator";

export const App: React.FC = () => {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<OverviewDashboard />} />
            <Route path="satellite" element={<SatelliteExplorer />} />
            <Route path="lakes" element={<GlacialLakeDetection />} />
            <Route path="change-analysis" element={<HistoricalChangeAnalysis />} />
            <Route path="disaster-impact" element={<DisasterImpactAnalysis />} />
            <Route path="glacier" element={<GlacierMonitoring />} />
            <Route path="susceptibility" element={<GlofSusceptibility />} />
            <Route path="flood-simulation" element={<FloodSimulation />} />
            <Route path="exposure" element={<InfrastructureExposure />} />
            <Route path="workspace" element={<GeoTiffWorkspace />} />
            <Route path="model-lab" element={<ModelLab />} />
            <Route path="reports" element={<ReportGenerator />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
};

export default App;
