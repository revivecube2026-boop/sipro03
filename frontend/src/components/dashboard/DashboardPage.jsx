import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import {
  Building2, Grid3X3, Users, Handshake, TrendingUp, ArrowUpRight,
  Clock, DollarSign, HardHat, Bell, Calendar,
  ChevronRight, Target, UserCheck, Phone, AlertTriangle, Layers,
  Megaphone, MessageCircle, UserPlus, BarChart3
} from 'lucide-react';

function fmt(num) {
  if (!num) return 'Rp 0';
  if (num >= 1e9) return `Rp ${(num / 1e9).toFixed(1)}M`;
  if (num >= 1e6) return `Rp ${(num / 1e6).toFixed(0)}Jt`;
  return `Rp ${num.toLocaleString('id-ID')}`;
}

const STAGE_COLORS = {
  acquisition: { bg: 'rgba(37,99,235,0.08)', color: '#2563eb', label: 'Akuisisi' },
  nurturing: { bg: 'rgba(245,158,11,0.08)', color: '#f59e0b', label: 'Nurturing' },
  appointment: { bg: 'rgba(124,58,237,0.08)', color: '#7c3aed', label: 'Appointment' },
  booking: { bg: 'rgba(16,185,129,0.08)', color: '#10b981', label: 'Booking' },
  recycle: { bg: 'rgba(148,163,184,0.08)', color: '#8896ab', label: 'Recycle' },
};

function getDashboardMode(role) {
  if (['super_admin', 'owner', 'general_manager'].includes(role)) return 'management';
  if (['sales_manager', 'marketing_admin'].includes(role)) return 'marketing_admin';
  if (['sales', 'marketing_inhouse'].includes(role)) return 'marketing_inhouse';
  if (['finance', 'accounting', 'collection'].includes(role)) return 'finance';
  if (['project_manager', 'site_engineer'].includes(role)) return 'project';
  return 'management';
}

function getModeLabel(mode) {
  const labels = {
    management: 'Management Overview',
    marketing_admin: 'Marketing Admin',
    marketing_inhouse: 'Marketing Inhouse',
    finance: 'Finance',
    project: 'Project'
  };
  return labels[mode] || 'Dashboard';
}

// Reusable KPI card
function KpiCard({ icon: Icon, label, value, sub, color, path, isText, onClick }) {
  return (
    <div className="mini-dashboard-card glass-card-clickable" onClick={onClick} data-testid={`kpi-${label}`}
      style={{ padding: '10px 12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 2 }}>
        <Icon size={13} color={color} style={{ opacity: 0.8 }} />
        {path && <ArrowUpRight size={9} color="#8896ab" />}
      </div>
      <div className="kpi-number" style={{ fontSize: isText ? 13 : 18 }}>{value}</div>
      <div className="kpi-label" style={{ fontSize: 8 }}>{label}</div>
      {sub && <div style={{ fontSize: 8, color: '#8896ab', marginTop: 1 }}>{sub}</div>}
    </div>
  );
}

// Task card
function TaskCard({ task, onClick }) {
  return (
    <div className={`task-card task-card-${task.type}`} onClick={onClick} data-testid={`task-${task.title}`}
      style={{ padding: '8px 12px' }}>
      <task.icon size={13} color={task.color} style={{ marginTop: 1, flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#1a2236' }}>{task.title}</div>
        <div style={{ fontSize: 9, color: '#8896ab' }}>{task.desc}</div>
      </div>
      <ChevronRight size={11} color="#8896ab" />
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [pipelineData, setPipelineData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const { t } = useLang();
  const navigate = useNavigate();

  const viewMode = user ? getDashboardMode(user.role) : 'management';

  useEffect(() => { loadData(); }, [user]);

  const loadData = async () => {
    try {
      const [dashRes, pipeRes] = await Promise.all([
        api.get('/dashboard'),
        api.get('/leads/pipeline')
      ]);
      setData(dashRes.data.data);
      setPipelineData(pipeRes.data.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  if (loading) return <div style={{ padding: 30, textAlign: 'center', color: '#8896ab', fontSize: 12 }}>{t('loading')}</div>;
  const d = data || {};
  const pl = pipelineData || {};
  const stages = pl.stages || {};
  const myLeads = d.my_leads || {};

  // Build task queue based on role
  const tasks = [];
  if (viewMode === 'management' || viewMode === 'marketing_admin') {
    if (d.unassigned_leads > 0) tasks.push({ type: 'urgent', icon: UserPlus, title: `${d.unassigned_leads} Lead Belum Ditugaskan`, desc: 'Perlu distribusi ke tim', path: '/crm?stage=acquisition', color: '#ef4444' });
    if (d.leads_not_contacted > 0) tasks.push({ type: 'urgent', icon: Phone, title: `${d.leads_not_contacted} Lead Belum Dihubungi`, desc: 'Stage: Akuisisi — perlu initial contact', path: '/crm?stage=acquisition', color: '#ef4444' });
    if (stages.nurturing > 0) tasks.push({ type: 'warning', icon: UserCheck, title: `${stages.nurturing} Lead Nurturing`, desc: 'Sedang proses follow-up', path: '/crm?stage=nurturing', color: '#f59e0b' });
  }
  if (viewMode === 'marketing_inhouse') {
    if (myLeads.acquisition > 0) tasks.push({ type: 'urgent', icon: Phone, title: `${myLeads.acquisition} Lead Perlu Dihubungi`, desc: 'Assigned ke Anda — segera follow up', path: '/crm?stage=acquisition', color: '#ef4444' });
    if (myLeads.nurturing > 0) tasks.push({ type: 'warning', icon: MessageCircle, title: `${myLeads.nurturing} Lead Nurturing`, desc: 'Follow-up lanjutan diperlukan', path: '/crm?stage=nurturing', color: '#f59e0b' });
    if (d.my_appointments > 0) tasks.push({ type: 'info', icon: Calendar, title: `${d.my_appointments} Jadwal Aktif`, desc: 'Survey / appointment terjadwal', path: '/appointments', color: '#2563eb' });
  }
  if (viewMode === 'management' || viewMode === 'finance') {
    if (d.finance?.outstanding > 0) tasks.push({ type: 'warning', icon: DollarSign, title: `Outstanding ${fmt(d.finance.outstanding)}`, desc: `${d.overdue_payments || 0} billing overdue`, path: '/finance', color: '#ef4444' });
  }
  if (viewMode === 'management' || viewMode === 'project') {
    if (d.construction?.in_progress > 0) tasks.push({ type: 'info', icon: HardHat, title: `${d.construction.in_progress} Konstruksi Berjalan`, desc: 'Monitor progress', path: '/construction', color: '#0ea5e9' });
  }
  if (d.notifications?.unread > 0) tasks.push({ type: 'info', icon: Bell, title: `${d.notifications.unread} Notifikasi`, desc: 'Belum dibaca', path: '/notifications', color: '#7c3aed' });
  (d.upcoming_appointments || []).slice(0, 2).forEach(a => {
    tasks.push({ type: 'info', icon: Calendar, title: `Jadwal: ${a.lead_name || a.status}`, desc: new Date(a.scheduled_at).toLocaleString('id-ID', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }), path: '/appointments', color: '#2563eb' });
  });

  return (
    <div className="animate-fade-in" data-testid="dashboard-page">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em', color: '#1a2236' }}>
            Selamat Datang, {user?.name || 'Admin'}
          </h1>
          <p style={{ color: '#8896ab', fontSize: 11, marginTop: 1 }}>
            Dashboard {getModeLabel(viewMode)} &middot; {user?.role?.replace('_', ' ')}
          </p>
        </div>
        <div style={{ background: 'rgba(37,99,235,0.06)', padding: '4px 10px', borderRadius: 6, fontSize: 10, fontWeight: 700, color: '#2563eb' }}>
          {getModeLabel(viewMode)}
        </div>
      </div>

      {/* Lead Lifecycle Funnel — visible for management & marketing */}
      {(viewMode === 'management' || viewMode === 'marketing_admin' || viewMode === 'marketing_inhouse') && (
        <div className="glass-card" style={{ padding: '10px 14px', marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <Layers size={13} color="#2563eb" />
            <span style={{ fontSize: 12, fontWeight: 800 }}>Lead Lifecycle</span>
            <span style={{ fontSize: 9, color: '#8896ab', marginLeft: 'auto' }}>{pl.total || 0} total</span>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {(pl.funnel || []).map((f) => {
              const sc = STAGE_COLORS[f.stage] || STAGE_COLORS.recycle;
              return (
                <div key={f.stage} className="glass-card-clickable" onClick={() => navigate(`/crm?stage=${f.stage}`)}
                  style={{ flex: 1, background: sc.bg, borderRadius: 8, padding: '8px 6px', textAlign: 'center', cursor: 'pointer', border: '1px solid transparent', transition: 'all 0.15s ease' }}
                  data-testid={`funnel-${f.stage}`}
                  onMouseEnter={e => e.currentTarget.style.borderColor = sc.color}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'transparent'}>
                  <div style={{ fontSize: 18, fontWeight: 800, color: sc.color, lineHeight: 1 }}>{f.count}</div>
                  <div style={{ fontSize: 8, fontWeight: 700, color: sc.color, textTransform: 'uppercase', marginTop: 2 }}>{sc.label}</div>
                  <div style={{ fontSize: 8, color: '#8896ab' }}>{f.pct}%</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* KPI Row - role-specific */}
      <div className="mini-dashboard stagger-children" style={{ gridTemplateColumns: viewMode === 'finance' ? 'repeat(4, 1fr)' : viewMode === 'marketing_inhouse' ? 'repeat(4, 1fr)' : 'repeat(6, 1fr)', gap: 6, marginBottom: 10 }}>
        {/* Management KPIs */}
        {viewMode === 'management' && [
          { label: t('total_projects'), value: d.projects?.total || 0, sub: `${d.projects?.active || 0} aktif`, icon: Building2, color: '#2563eb', path: '/projects' },
          { label: t('total_units'), value: d.units?.total || 0, sub: `${d.units?.sold || 0} terjual`, icon: Grid3X3, color: '#10b981', path: '/units' },
          { label: t('total_leads'), value: d.leads?.total || 0, sub: `${d.unassigned_leads || 0} unassigned`, icon: Users, color: '#f59e0b', path: '/crm' },
          { label: t('total_deals'), value: d.deals?.total || 0, sub: `${d.deals?.active || 0} aktif`, icon: Handshake, color: '#7c3aed', path: '/deals' },
          { label: t('revenue'), value: fmt(d.revenue?.total), sub: 'realisasi', icon: TrendingUp, color: '#0ea5e9', isText: true },
          { label: 'Collection', value: fmt(d.finance?.paid), sub: fmt(d.finance?.outstanding) + ' sisa', icon: DollarSign, color: '#ef4444', path: '/finance', isText: true },
        ].map((kpi, i) => (
          <KpiCard key={i} {...kpi} onClick={() => kpi.path && navigate(kpi.path)} />
        ))}

        {/* Marketing Admin KPIs */}
        {viewMode === 'marketing_admin' && [
          { label: t('total_leads'), value: d.leads?.total || 0, sub: `${d.unassigned_leads || 0} belum ditugaskan`, icon: Users, color: '#2563eb', path: '/crm' },
          { label: 'Akuisisi', value: d.lead_stages?.acquisition || 0, sub: 'lead baru', icon: Target, color: '#f59e0b', path: '/crm?stage=acquisition' },
          { label: 'Nurturing', value: d.lead_stages?.nurturing || 0, sub: 'proses follow-up', icon: Phone, color: '#7c3aed', path: '/crm?stage=nurturing' },
          { label: 'Appointment', value: d.lead_stages?.appointment || 0, sub: 'jadwal survey', icon: Calendar, color: '#0ea5e9', path: '/crm?stage=appointment' },
          { label: 'Booking', value: d.lead_stages?.booking || 0, sub: 'konversi', icon: Handshake, color: '#10b981', path: '/crm?stage=booking' },
          { label: 'Recycle', value: d.lead_stages?.recycle || 0, sub: 'inactive', icon: AlertTriangle, color: '#8896ab', path: '/crm?stage=recycle' },
        ].map((kpi, i) => (
          <KpiCard key={i} {...kpi} onClick={() => kpi.path && navigate(kpi.path)} />
        ))}

        {/* Marketing Inhouse KPIs */}
        {viewMode === 'marketing_inhouse' && [
          { label: 'Lead Saya', value: myLeads.total || 0, sub: 'assigned ke Anda', icon: Users, color: '#2563eb', path: '/crm' },
          { label: 'Perlu Kontak', value: myLeads.acquisition || 0, sub: 'belum dihubungi', icon: Phone, color: '#ef4444', path: '/crm?stage=acquisition' },
          { label: 'Nurturing', value: myLeads.nurturing || 0, sub: 'follow-up', icon: MessageCircle, color: '#f59e0b', path: '/crm?stage=nurturing' },
          { label: 'Jadwal', value: d.my_appointments || 0, sub: 'appointment aktif', icon: Calendar, color: '#7c3aed', path: '/appointments' },
        ].map((kpi, i) => (
          <KpiCard key={i} {...kpi} onClick={() => kpi.path && navigate(kpi.path)} />
        ))}

        {/* Finance KPIs */}
        {viewMode === 'finance' && [
          { label: 'Total Tagihan', value: fmt(d.finance?.total_billing), icon: DollarSign, color: '#2563eb', path: '/finance', isText: true },
          { label: 'Terbayar', value: fmt(d.finance?.paid), icon: TrendingUp, color: '#10b981', path: '/finance', isText: true },
          { label: 'Outstanding', value: fmt(d.finance?.outstanding), icon: AlertTriangle, color: '#f59e0b', path: '/finance', isText: true },
          { label: 'Overdue', value: d.overdue_payments || 0, icon: Clock, color: '#ef4444', path: '/finance' },
        ].map((kpi, i) => (
          <KpiCard key={i} {...kpi} onClick={() => kpi.path && navigate(kpi.path)} />
        ))}

        {/* Project KPIs */}
        {viewMode === 'project' && [
          { label: t('total_projects'), value: d.projects?.total || 0, sub: `${d.projects?.active || 0} aktif`, icon: Building2, color: '#2563eb', path: '/projects' },
          { label: 'Konstruksi', value: d.construction?.in_progress || 0, sub: 'berjalan', icon: HardHat, color: '#0ea5e9', path: '/construction' },
          { label: 'Selesai', value: d.construction?.completed || 0, sub: 'unit', icon: Target, color: '#10b981', path: '/construction' },
          { label: t('total_units'), value: d.units?.total || 0, sub: `${d.units?.sold || 0} terjual`, icon: Grid3X3, color: '#f59e0b', path: '/units' },
          { label: t('revenue'), value: fmt(d.revenue?.total), icon: TrendingUp, color: '#7c3aed', isText: true },
          { label: 'Collection', value: fmt(d.finance?.paid), sub: fmt(d.finance?.outstanding) + ' sisa', icon: DollarSign, color: '#ef4444', path: '/finance', isText: true },
        ].map((kpi, i) => (
          <KpiCard key={i} {...kpi} onClick={() => kpi.path && navigate(kpi.path)} />
        ))}
      </div>

      {/* Main Grid - 3 columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 8 }}>
        {/* Task Queue */}
        <div className="glass-card" style={{ padding: 10 }}>
          <div className="section-header" style={{ marginBottom: 8 }}>
            <div>
              <div className="section-title" style={{ fontSize: 12 }}>Task Queue</div>
              <div className="section-subtitle" style={{ fontSize: 9 }}>Yang perlu dilakukan</div>
            </div>
            {tasks.length > 0 && <span style={{ fontSize: 9, fontWeight: 800, color: '#ef4444', background: 'rgba(239,68,68,0.08)', padding: '2px 6px', borderRadius: 5 }}>{tasks.length}</span>}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 240, overflowY: 'auto' }}>
            {tasks.map((task, i) => (
              <TaskCard key={i} task={task} onClick={() => navigate(task.path)} />
            ))}
            {tasks.length === 0 && <div style={{ fontSize: 10, color: '#8896ab', textAlign: 'center', padding: 14 }}>Semua aman!</div>}
          </div>
        </div>

        {/* Middle Card — role-dependent */}
        {(viewMode === 'management' || viewMode === 'marketing_admin' || viewMode === 'marketing_inhouse') && (
          <div className="glass-card" style={{ padding: 10 }}>
            <div className="section-header" style={{ marginBottom: 8 }}>
              <div className="section-title" style={{ fontSize: 12 }}>{t('unit_summary')}</div>
              <button className="btn-pill btn-pill-secondary" onClick={() => navigate('/siteplan')} style={{ fontSize: 8, padding: '2px 6px' }}>Siteplan</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 5, marginBottom: 6 }}>
              {[
                { label: t('available'), value: d.units?.available || 0, color: '#8896ab' },
                { label: t('reserved'), value: d.units?.reserved || 0, color: '#f59e0b' },
                { label: t('booked'), value: d.units?.booked || 0, color: '#f97316' },
                { label: t('sold'), value: d.units?.sold || 0, color: '#10b981' },
              ].map((s, i) => (
                <div key={i} style={{ background: `${s.color}10`, borderRadius: 6, padding: '5px 6px', textAlign: 'center' }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: 8, fontWeight: 700, color: '#8896ab', textTransform: 'uppercase' }}>{s.label}</div>
                </div>
              ))}
            </div>
            <div className="progress-bar" style={{ marginBottom: 3 }}>
              <div className="progress-bar-fill" style={{ width: `${((d.units?.sold || 0) / Math.max(d.units?.total || 1, 1)) * 100}%`, background: '#10b981' }} />
            </div>
            <div style={{ fontSize: 8, color: '#8896ab' }}>{d.units?.sold || 0} / {d.units?.total || 0} unit terjual</div>
          </div>
        )}
        {viewMode === 'finance' && (
          <div className="glass-card" style={{ padding: 10 }}>
            <div className="section-header" style={{ marginBottom: 8 }}>
              <div className="section-title" style={{ fontSize: 12 }}>Collection Rate</div>
              <button className="btn-pill btn-pill-secondary" onClick={() => navigate('/finance')} style={{ fontSize: 8, padding: '2px 6px' }}>Detail</button>
            </div>
            {d.finance?.total_billing > 0 && (
              <>
                <div style={{ textAlign: 'center', margin: '8px 0' }}>
                  <div style={{ fontSize: 28, fontWeight: 800, color: '#2563eb' }}>{Math.round((d.finance.paid / d.finance.total_billing) * 100)}%</div>
                  <div style={{ fontSize: 9, color: '#8896ab' }}>dari {fmt(d.finance.total_billing)}</div>
                </div>
                <div className="progress-bar" style={{ height: 6, borderRadius: 3 }}>
                  <div className="progress-bar-fill" style={{ width: `${(d.finance.paid / d.finance.total_billing) * 100}%`, background: 'linear-gradient(90deg, #10b981, #2563eb)', borderRadius: 3 }} />
                </div>
              </>
            )}
          </div>
        )}
        {viewMode === 'project' && (
          <div className="glass-card" style={{ padding: 10 }}>
            <div className="section-header" style={{ marginBottom: 8 }}>
              <div className="section-title" style={{ fontSize: 12 }}>{t('construction')}</div>
              <button className="btn-pill btn-pill-secondary" onClick={() => navigate('/construction')} style={{ fontSize: 8, padding: '2px 6px' }}>Detail</button>
            </div>
            <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
              {[
                { label: 'Berjalan', value: d.construction?.in_progress || 0, color: '#0ea5e9' },
                { label: 'Selesai', value: d.construction?.completed || 0, color: '#10b981' },
                { label: 'Total', value: d.construction?.total || 0, color: '#1a2236' },
              ].map((item, i) => (
                <div key={i} style={{ flex: 1, textAlign: 'center', background: `${item.color}08`, borderRadius: 6, padding: '6px 0' }}>
                  <div style={{ fontSize: 18, fontWeight: 800, color: item.color }}>{item.value}</div>
                  <div style={{ fontSize: 8, color: '#8896ab' }}>{item.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Right Card — Lead Sources + Activities */}
        <div className="glass-card" style={{ padding: 10 }}>
          <div className="section-header" style={{ marginBottom: 6 }}>
            <div className="section-title" style={{ fontSize: 12 }}>{t('lead_sources')}</div>
            <button className="btn-pill btn-pill-secondary" onClick={() => navigate('/lead-import')} style={{ fontSize: 8, padding: '2px 6px' }}>Import</button>
          </div>
          {(d.lead_sources || []).slice(0, 5).map((src, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '2px 0' }}>
              <span style={{ fontSize: 10, fontWeight: 600, color: '#556680', textTransform: 'capitalize' }}>{src.source?.replace('_', ' ')}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div className="progress-bar" style={{ width: 36 }}><div className="progress-bar-fill" style={{ width: `${(src.count / Math.max(d.leads?.total || 1, 1)) * 100}%`, background: '#2563eb' }} /></div>
                <span style={{ fontSize: 9, fontWeight: 800, minWidth: 12, textAlign: 'right' }}>{src.count}</span>
              </div>
            </div>
          ))}
          <div style={{ borderTop: '1px solid rgba(0,0,0,0.04)', marginTop: 6, paddingTop: 6 }}>
            <div className="section-title" style={{ fontSize: 10, marginBottom: 3 }}>{t('recent_activities')}</div>
            <div style={{ maxHeight: 80, overflowY: 'auto' }}>
              {(d.recent_events || []).slice(0, 4).map((evt, i) => (
                <div key={i} style={{ display: 'flex', gap: 5, padding: '2px 0' }}>
                  <div style={{ width: 3, height: 3, borderRadius: '50%', background: '#2563eb', marginTop: 5, flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: 9, fontWeight: 600, color: '#556680' }}>{evt.type?.replace('.', ' ').replace('_', ' ')}</div>
                    <div style={{ fontSize: 8, color: '#8896ab' }}>{new Date(evt.created_at).toLocaleString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Row — Quick Access Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
        <div className="glass-card glass-card-clickable" style={{ padding: 10 }} onClick={() => navigate('/finance')} data-testid="dashboard-finance">
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 4 }}>
            <DollarSign size={12} color="#2563eb" /><span style={{ fontSize: 11, fontWeight: 800 }}>Finance</span>
            <ArrowUpRight size={9} color="#8896ab" style={{ marginLeft: 'auto' }} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <div><div style={{ fontSize: 12, fontWeight: 800, color: '#10b981' }}>{fmt(d.finance?.paid)}</div><div style={{ fontSize: 8, color: '#8896ab' }}>Terbayar</div></div>
            <div><div style={{ fontSize: 12, fontWeight: 800, color: '#f59e0b' }}>{fmt(d.finance?.outstanding)}</div><div style={{ fontSize: 8, color: '#8896ab' }}>Outstanding</div></div>
          </div>
        </div>

        <div className="glass-card glass-card-clickable" style={{ padding: 10 }} onClick={() => navigate('/construction')} data-testid="dashboard-construction">
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 4 }}>
            <HardHat size={12} color="#f59e0b" /><span style={{ fontSize: 11, fontWeight: 800 }}>{t('construction')}</span>
            <ArrowUpRight size={9} color="#8896ab" style={{ marginLeft: 'auto' }} />
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <span style={{ fontSize: 10, color: '#0ea5e9', fontWeight: 700 }}>{d.construction?.in_progress || 0} berjalan</span>
            <span style={{ fontSize: 10, color: '#10b981', fontWeight: 700 }}>{d.construction?.completed || 0} selesai</span>
          </div>
        </div>

        <div className="glass-card glass-card-clickable" style={{ padding: 10 }} onClick={() => navigate('/notifications')} data-testid="dashboard-notifications">
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 4 }}>
            <Bell size={12} color="#7c3aed" /><span style={{ fontSize: 11, fontWeight: 800 }}>{t('notifications')}</span>
            {(d.notifications?.unread || 0) > 0 && <span style={{ background: '#ef4444', color: 'white', borderRadius: 4, padding: '1px 4px', fontSize: 8, fontWeight: 800, marginLeft: 'auto' }}>{d.notifications.unread}</span>}
          </div>
          <div style={{ fontSize: 10, color: '#556680' }}>{(d.notifications?.unread || 0) > 0 ? `${d.notifications.unread} notifikasi baru` : 'Semua dibaca'}</div>
        </div>
      </div>
    </div>
  );
}
