import { Spin } from 'antd';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth';
import { Shell } from './components/Shell';
import { AssistantPage } from './pages/AssistantPage';
import { AuditPage } from './pages/AuditPage';
import { BatchesPage } from './pages/BatchesPage';
import { DashboardPage } from './pages/DashboardPage';
import { FilesPage } from './pages/FilesPage';
import { LoginPage } from './pages/LoginPage';
import { TasksPage } from './pages/TasksPage';

export function App() {
  const { user, loading, hasRole } = useAuth();
  if (loading) return <div className="full-spin"><Spin size="large" /></div>;
  if (!user) return <LoginPage />;
  return <Shell><Routes>
    <Route path="/" element={<DashboardPage />} />
    <Route path="/batches" element={<BatchesPage />} />
    <Route path="/tasks" element={hasRole('admin', 'operator', 'approver') ? <TasksPage /> : <Navigate to="/" replace />} />
    <Route path="/assistant" element={<AssistantPage />} />
    <Route path="/files" element={<FilesPage />} />
    <Route path="/audit" element={hasRole('admin', 'approver') ? <AuditPage /> : <Navigate to="/" replace />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></Shell>;
}
