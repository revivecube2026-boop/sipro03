import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LanguageProvider } from './contexts/LanguageContext';
import Sidebar from './components/layout/Sidebar';
import LoginPage from './components/auth/LoginPage';
import DashboardPage from './components/dashboard/DashboardPage';
import ProjectsPage from './components/projects/ProjectsPage';
import UnitsPage from './components/units/UnitsPage';
import SiteplanPage from './components/siteplan/SiteplanPage';
import CRMPage from './components/crm/CRMPage';
import LeadImportPage from './components/crm/LeadImportPage';
import DealsPage from './components/deals/DealsPage';
import WhatsAppPage from './components/whatsapp/WhatsAppPage';
import DevReportPage from './components/dev-report/DevReportPage';
import FinancePage from './components/finance/FinancePage';
import ConstructionPage from './components/construction/ConstructionPage';
import NotificationsPage from './components/notifications/NotificationsPage';
import AppointmentsPage from './components/appointments/AppointmentsPage';
import './App.css';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#f0f2f5'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: 48, height: 48, borderRadius: 14,
            background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px', color: 'white', fontWeight: 800, fontSize: 20
          }}>S</div>
          <div style={{ color: '#64748b', fontSize: 14, fontWeight: 500 }}>Loading SIPRO...</div>
        </div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppLayout() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'linear-gradient(145deg, #e8edf5 0%, #dce3f0 30%, #d4dced 60%, #e0e7f2 100%)' }}>
      <Sidebar />
      <div className="sipro-content">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/units" element={<UnitsPage />} />
          <Route path="/siteplan" element={<SiteplanPage />} />
          <Route path="/crm" element={<CRMPage />} />
          <Route path="/lead-import" element={<LeadImportPage />} />
          <Route path="/deals" element={<DealsPage />} />
          <Route path="/whatsapp" element={<WhatsAppPage />} />
          <Route path="/dev-report" element={<DevReportPage />} />
          <Route path="/finance" element={<FinancePage />} />
          <Route path="/construction" element={<ConstructionPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/appointments" element={<AppointmentsPage />} />
        </Routes>
      </div>
    </div>
  );
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) return null;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/*" element={
        <ProtectedRoute>
          <AppLayout />
        </ProtectedRoute>
      } />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <LanguageProvider>
          <AppRoutes />
        </LanguageProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
