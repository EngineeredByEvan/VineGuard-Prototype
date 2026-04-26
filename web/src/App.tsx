import { Route, Routes } from 'react-router-dom';

import { Layout } from './components/Layout';
import { AlertsCenter } from './pages/AlertsCenter';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { BlockDetail } from './pages/BlockDetail';
import { BlocksPage } from './pages/BlocksPage';
import { NodeDetail } from './pages/NodeDetail';
import { Overview } from './pages/Overview';
import { Recommendations } from './pages/Recommendations';
import { SettingsPage } from './pages/SettingsPage';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="blocks" element={<BlocksPage />} />
        <Route path="blocks/:blockId" element={<BlockDetail />} />
        <Route path="nodes/:nodeId" element={<NodeDetail />} />
        <Route path="alerts" element={<AlertsCenter />} />
        <Route path="recommendations" element={<Recommendations />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
