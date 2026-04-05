import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useLang } from '../../contexts/LanguageContext';
import {
  LayoutDashboard, Building2, Grid3X3, Map, Users, Handshake,
  MessageCircle, FileText, LogOut, ChevronLeft, ChevronRight,
  Import, Globe, DollarSign, HardHat, Bell, Calendar,
  Target, Phone, UserCheck, RefreshCw, Megaphone
} from 'lucide-react';

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();
  const { t, lang, toggleLang } = useLang();
  const navigate = useNavigate();

  const handleLogout = async () => { await logout(); navigate('/login'); };

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: t('dashboard') },

    { divider: true, label: 'Lead Lifecycle' },
    { path: '/crm', icon: Users, label: 'Overview', query: '' },
    { path: '/crm', icon: Target, label: 'Akuisisi', query: '?stage=acquisition', badge: 'acq' },
    { path: '/crm', icon: Phone, label: 'Nurturing', query: '?stage=nurturing', badge: 'nur' },
    { path: '/crm', icon: Calendar, label: 'Appointment', query: '?stage=appointment', badge: 'apt' },
    { path: '/crm', icon: Handshake, label: 'Booking', query: '?stage=booking', badge: 'bkg' },
    { path: '/crm', icon: RefreshCw, label: 'Recycle', query: '?stage=recycle', badge: 'rec' },

    { divider: true, label: 'Property' },
    { path: '/projects', icon: Building2, label: t('projects') },
    { path: '/units', icon: Grid3X3, label: t('units') },
    { path: '/siteplan', icon: Map, label: t('siteplan') },

    { divider: true, label: 'Sales' },
    { path: '/lead-import', icon: Import, label: t('lead_import') },
    { path: '/deals', icon: Handshake, label: t('deals') },
    { path: '/appointments', icon: Calendar, label: t('appointments') },

    { divider: true, label: 'Operations' },
    { path: '/finance', icon: DollarSign, label: 'Finance' },
    { path: '/construction', icon: HardHat, label: t('construction') },

    { divider: true, label: 'Comms' },
    { path: '/whatsapp', icon: MessageCircle, label: 'WhatsApp' },
    { path: '/notifications', icon: Bell, label: t('notifications') },

    { divider: true, label: 'System' },
    { path: '/dev-report', icon: FileText, label: t('dev_report') },
  ];

  return (
    <div className={`sipro-sidebar ${collapsed ? 'sipro-sidebar-collapsed' : ''}`} data-testid="sidebar">
      {/* Logo */}
      <div style={{ padding: '12px 10px', display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div style={{
          width: 30, height: 30, borderRadius: 8, background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 800, fontSize: 13, flexShrink: 0
        }}>S</div>
        {!collapsed && (
          <div>
            <div style={{ color: '#e2e8f0', fontWeight: 800, fontSize: 14, letterSpacing: '-0.02em', lineHeight: 1 }}>SIPRO</div>
            <div style={{ color: '#4b5e78', fontSize: 8, fontWeight: 600, letterSpacing: '0.06em' }}>PROPERTY OS</div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '4px 0', overflowY: 'auto' }}>
        {navItems.map((item, idx) => {
          if (item.divider) {
            if (collapsed) return null;
            return <div key={idx} style={{ padding: '8px 14px 2px', fontSize: 8, fontWeight: 700, color: '#3d5068', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{item.label}</div>;
          }

          // For stage-filtered CRM links, use onClick navigation instead of NavLink
          if (item.query !== undefined) {
            const fullPath = item.path + item.query;
            const isActive = window.location.pathname === item.path && window.location.search === item.query;
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => navigate(fullPath)}
                data-testid={`nav-lifecycle-${item.badge || 'overview'}`}
                title={collapsed ? item.label : undefined}
                style={{ cursor: 'pointer', fontSize: 12, padding: '5px 10px' }}
              >
                <Icon size={15} />
                {!collapsed && <span>{item.label}</span>}
              </div>
            );
          }

          const Icon = item.icon;
          return (
            <NavLink key={item.path + idx} to={item.path} end={item.path === '/'}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
              data-testid={`nav-${item.path.replace('/', '') || 'dashboard'}`}
              title={collapsed ? item.label : undefined}
              style={{ fontSize: 12, padding: '5px 10px' }}
            >
              <Icon size={15} />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom */}
      <div style={{ padding: '6px 4px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <button onClick={toggleLang} className="sidebar-nav-item" style={{ width: '100%', border: 'none', background: 'none', fontSize: 11, padding: '4px 10px' }} data-testid="lang-toggle">
          <Globe size={14} />{!collapsed && <span>{lang === 'id' ? 'EN' : 'ID'}</span>}
        </button>
        {user && (
          <>
            <div className="sidebar-nav-item" style={{ cursor: 'default', opacity: 0.7, padding: '4px 10px' }}>
              <div style={{ width: 22, height: 22, borderRadius: '50%', background: '#1e3a5f', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, fontWeight: 800, color: '#7b8ca5', flexShrink: 0 }}>
                {(user.name || user.email || '?')[0].toUpperCase()}
              </div>
              {!collapsed && (
                <div style={{ overflow: 'hidden' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#c8d6e5', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user.name || user.email}</div>
                  <div style={{ fontSize: 8, color: '#4b5e78' }}>{user.role?.replace('_', ' ')}</div>
                </div>
              )}
            </div>
            <button onClick={handleLogout} className="sidebar-nav-item" style={{ width: '100%', border: 'none', background: 'none', color: '#ef4444', fontSize: 11, padding: '4px 10px' }} data-testid="logout-btn">
              <LogOut size={14} />{!collapsed && <span>{t('logout')}</span>}
            </button>
          </>
        )}
        <button onClick={() => setCollapsed(!collapsed)} className="sidebar-nav-item" style={{ width: '100%', border: 'none', background: 'none', justifyContent: collapsed ? 'center' : 'flex-start', fontSize: 11, padding: '4px 10px' }} data-testid="sidebar-collapse-btn">
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </div>
  );
}
