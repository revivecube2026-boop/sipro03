import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import {
  Users, Plus, Search, Phone, ArrowRight, Layers, Target, RefreshCw,
  Calendar, Handshake, UserPlus, UserCheck, X, Clock, Check,
  XCircle, ChevronRight, MessageCircle, Activity, History, Zap
} from 'lucide-react';

const STAGE_CONFIG = {
  acquisition: { label: 'Akuisisi', color: '#2563eb', bg: 'rgba(37,99,235,0.08)', icon: Target },
  nurturing: { label: 'Nurturing', color: '#f59e0b', bg: 'rgba(245,158,11,0.08)', icon: Phone },
  appointment: { label: 'Appointment', color: '#7c3aed', bg: 'rgba(124,58,237,0.08)', icon: Calendar },
  booking: { label: 'Booking', color: '#10b981', bg: 'rgba(16,185,129,0.08)', icon: Handshake },
  recycle: { label: 'Recycle', color: '#8896ab', bg: 'rgba(148,163,184,0.08)', icon: RefreshCw },
};

function StageBadge({ stage }) {
  const sc = STAGE_CONFIG[stage] || STAGE_CONFIG.acquisition;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, fontWeight: 700, color: sc.color, background: sc.bg, padding: '2px 8px', borderRadius: 6 }}>
      <sc.icon size={10} />{sc.label}
    </span>
  );
}

function AssignBadge({ assignedTo, status }) {
  if (!assignedTo) return <span style={{ fontSize: 10, color: '#ef4444', fontWeight: 600 }}>Unassigned</span>;
  const color = status === 'accepted' ? '#10b981' : status === 'rejected' ? '#ef4444' : '#f59e0b';
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#556680' }}>{assignedTo.split('@')[0]}</div>
      {status && <span style={{ fontSize: 8, fontWeight: 700, color, textTransform: 'uppercase' }}>{status}</span>}
    </div>
  );
}

function ResponseTimeBadge({ minutes }) {
  if (!minutes && minutes !== 0) return null;
  const color = minutes <= 30 ? '#10b981' : minutes <= 120 ? '#f59e0b' : '#ef4444';
  const label = minutes < 60 ? `${minutes}m` : `${Math.round(minutes / 60)}h`;
  return <span style={{ fontSize: 9, fontWeight: 700, color, background: `${color}10`, padding: '1px 5px', borderRadius: 4 }}>{label}</span>;
}

export default function CRMPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { t } = useLang();

  const [leads, setLeads] = useState([]);
  const [users, setUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [pipeline, setPipeline] = useState(null);
  const [responseStats, setResponseStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({
    stage: searchParams.get('stage') || '',
    status: searchParams.get('status') || '',
    source: '',
    project_id: '',
    search: ''
  });
  const [showForm, setShowForm] = useState(false);
  const [showAssign, setShowAssign] = useState(false);
  const [selectedLeads, setSelectedLeads] = useState([]);
  const [assignTarget, setAssignTarget] = useState('');
  const [assignReason, setAssignReason] = useState('');
  const [form, setForm] = useState({ name: '', phone: '', email: '', source: 'manual', campaign: '', project_id: '', notes: '' });
  const [selectedLead, setSelectedLead] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [showTimeline, setShowTimeline] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [showReject, setShowReject] = useState(null);

  // Sync URL params
  useEffect(() => {
    const urlStage = searchParams.get('stage') || '';
    const urlStatus = searchParams.get('status') || '';
    setFilters(prev => ({ ...prev, stage: urlStage, status: urlStatus }));
  }, [searchParams]);

  useEffect(() => { loadProjects(); loadPipeline(); loadUsers(); loadResponseStats(); }, []);
  useEffect(() => { loadLeads(); }, [filters]);

  const loadProjects = async () => { try { const { data } = await api.get('/projects'); setProjects(data.data); } catch {} };
  const loadPipeline = async () => { try { const { data } = await api.get('/leads/pipeline'); setPipeline(data.data); } catch {} };
  const loadUsers = async () => { try { const { data } = await api.get('/users'); setUsers(data.data || []); } catch {} };
  const loadResponseStats = async () => { try { const { data } = await api.get('/leads/response-stats'); setResponseStats(data.data); } catch {} };

  const loadLeads = async () => {
    setLoading(true);
    try {
      const params = {};
      Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
      const { data } = await api.get('/leads', { params });
      setLeads(data.data);
      setTotal(data.total);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/leads', form);
      setShowForm(false);
      setForm({ name: '', phone: '', email: '', source: 'manual', campaign: '', project_id: '', notes: '' });
      loadLeads(); loadPipeline();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const transitionStage = async (leadId, newStage, reason) => {
    try {
      await api.post(`/leads/${leadId}/transition`, { stage: newStage, reason: reason || '' });
      loadLeads(); loadPipeline(); loadResponseStats();
      if (selectedLead?.id === leadId) {
        const { data } = await api.get(`/leads/${leadId}`);
        setSelectedLead(data.data);
      }
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const handleAssign = async () => {
    if (!assignTarget || selectedLeads.length === 0) return;
    try {
      await api.post('/leads/assign', { lead_ids: selectedLeads, assigned_to: assignTarget, reason: assignReason });
      setShowAssign(false); setSelectedLeads([]); setAssignTarget(''); setAssignReason('');
      loadLeads();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const handleAutoAssign = async () => {
    try {
      const { data } = await api.post('/leads/auto-assign', { stage: filters.stage || 'acquisition' });
      alert(`Auto-assigned ${data.data.assigned} leads`);
      loadLeads();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const handleRespondAssignment = async (leadId, action, reason) => {
    try {
      await api.post(`/leads/${leadId}/assignment/respond`, { lead_id: leadId, action, reason: reason || '' });
      setShowReject(null); setRejectReason('');
      loadLeads();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const loadTimeline = async (leadId) => {
    try {
      const { data } = await api.get(`/leads/${leadId}/timeline`);
      setTimeline(data.data || []);
      setShowTimeline(true);
    } catch (err) { console.error(err); }
  };

  const toggleSelect = (leadId) => {
    setSelectedLeads(prev => prev.includes(leadId) ? prev.filter(id => id !== leadId) : [...prev, leadId]);
  };

  const stages = pipeline?.stages || {};
  const sources = ['meta_ads', 'google_ads', 'tiktok_ads', 'referral', 'walk_in', 'website', 'event', 'manual', 'csv_import'];

  return (
    <div className="animate-fade-in" data-testid="crm-page">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>CRM - Lead Lifecycle</h1>
          <p style={{ color: '#8896ab', fontSize: 10, marginTop: 1 }}>Pipeline lead dengan lifecycle stages</p>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {selectedLeads.length > 0 && (
            <button className="btn-pill btn-pill-secondary" onClick={() => setShowAssign(true)} data-testid="assign-btn" style={{ fontSize: 10, padding: '5px 10px' }}>
              <UserPlus size={12} style={{ display: 'inline', marginRight: 3 }} />Assign ({selectedLeads.length})
            </button>
          )}
          <button className="btn-pill btn-pill-secondary" onClick={handleAutoAssign} data-testid="auto-assign-btn" style={{ fontSize: 10, padding: '5px 10px' }}>
            <Zap size={12} style={{ display: 'inline', marginRight: 3 }} />Auto Assign
          </button>
          <button className="btn-pill btn-pill-primary" onClick={() => setShowForm(true)} data-testid="add-lead-btn" style={{ fontSize: 10, padding: '5px 10px' }}>
            <Plus size={12} style={{ display: 'inline', marginRight: 3 }} />{t('add_new')}
          </button>
        </div>
      </div>

      {/* Response Time Mini Dashboard */}
      {responseStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, marginBottom: 8 }}>
          <div className="mini-dashboard-card" style={{ padding: '6px 10px' }}>
            <Clock size={11} color="#2563eb" /><div className="kpi-number" style={{ fontSize: 16 }}>{responseStats.avg_response_minutes ? `${Math.round(responseStats.avg_response_minutes)}m` : '-'}</div>
            <div className="kpi-label" style={{ fontSize: 8 }}>Avg Response Time</div>
          </div>
          <div className="mini-dashboard-card" style={{ padding: '6px 10px' }}>
            <Phone size={11} color="#10b981" /><div className="kpi-number" style={{ fontSize: 16 }}>{responseStats.count || 0}</div>
            <div className="kpi-label" style={{ fontSize: 8 }}>Contacted</div>
          </div>
          <div className="mini-dashboard-card" style={{ padding: '6px 10px' }}>
            <Users size={11} color="#ef4444" /><div className="kpi-number" style={{ fontSize: 16 }}>{responseStats.waiting_for_contact || 0}</div>
            <div className="kpi-label" style={{ fontSize: 8 }}>Waiting Contact</div>
          </div>
          <div className="mini-dashboard-card" style={{ padding: '6px 10px' }}>
            <Clock size={11} color="#f59e0b" /><div className="kpi-number" style={{ fontSize: 16 }}>{responseStats.avg_wait_minutes ? `${responseStats.avg_wait_minutes}m` : '-'}</div>
            <div className="kpi-label" style={{ fontSize: 8 }}>Avg Wait Time</div>
          </div>
        </div>
      )}

      {/* Lifecycle Funnel */}
      <div className="glass-card" style={{ padding: '8px 12px', marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
          <Layers size={13} color="#2563eb" />
          <span style={{ fontSize: 11, fontWeight: 800 }}>Lead Lifecycle</span>
          <span style={{ fontSize: 9, color: '#8896ab', marginLeft: 'auto' }}>{pipeline?.total || total} total</span>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {Object.entries(STAGE_CONFIG).map(([key, cfg]) => {
            const count = stages[key] || 0;
            const isActive = filters.stage === key;
            return (
              <div key={key}
                onClick={() => setFilters({ ...filters, stage: isActive ? '' : key, status: '' })}
                style={{
                  flex: 1, background: isActive ? cfg.color : cfg.bg, borderRadius: 8,
                  padding: '6px 4px', textAlign: 'center', cursor: 'pointer',
                  border: `1px solid ${isActive ? cfg.color : 'transparent'}`, transition: 'all 0.15s ease'
                }}
                data-testid={`stage-${key}`}>
                <cfg.icon size={12} color={isActive ? 'white' : cfg.color} style={{ margin: '0 auto 2px' }} />
                <div style={{ fontSize: 16, fontWeight: 800, color: isActive ? 'white' : cfg.color, lineHeight: 1 }}>{count}</div>
                <div style={{ fontSize: 7, fontWeight: 700, color: isActive ? 'rgba(255,255,255,0.8)' : cfg.color, textTransform: 'uppercase', marginTop: 1 }}>{cfg.label}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 160 }}>
          <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#8896ab' }} />
          <input className="sipro-search" placeholder="Cari nama, telepon, email..." value={filters.search} onChange={e => setFilters({ ...filters, search: e.target.value })} data-testid="lead-search" style={{ paddingLeft: 30 }} />
        </div>
        <select value={filters.source} onChange={e => setFilters({ ...filters, source: e.target.value })} style={{ padding: '6px 8px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 10, fontFamily: 'inherit', background: 'rgba(255,255,255,0.7)' }} data-testid="lead-source-filter">
          <option value="">All Sources</option>
          {sources.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
        <select value={filters.project_id} onChange={e => setFilters({ ...filters, project_id: e.target.value })} style={{ padding: '6px 8px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 10, fontFamily: 'inherit', background: 'rgba(255,255,255,0.7)' }} data-testid="lead-project-filter">
          <option value="">{t('all_projects')}</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        {(filters.stage || filters.status || filters.source || filters.project_id) && (
          <button className="btn-pill btn-pill-secondary" style={{ fontSize: 9, padding: '3px 8px', color: '#ef4444' }}
            onClick={() => setFilters({ stage: '', status: '', source: '', project_id: '', search: filters.search })} data-testid="clear-filters-btn">
            Clear Filters
          </button>
        )}
      </div>

      {/* Leads Table */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '6px 12px', borderBottom: '1px solid rgba(0,0,0,0.04)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 11, fontWeight: 700 }}>{total} Leads {filters.stage ? `- ${STAGE_CONFIG[filters.stage]?.label}` : ''}</span>
          {selectedLeads.length > 0 && <span style={{ fontSize: 9, color: '#2563eb', fontWeight: 700 }}>{selectedLeads.length} selected</span>}
        </div>
        <table className="sipro-table" data-testid="leads-table">
          <thead>
            <tr>
              <th style={{ width: 24 }}><input type="checkbox" onChange={e => setSelectedLeads(e.target.checked ? leads.map(l => l.id) : [])} checked={selectedLeads.length === leads.length && leads.length > 0} data-testid="select-all-leads" /></th>
              <th>{t('name')}</th>
              <th>{t('phone')}</th>
              <th>Stage</th>
              <th>Assigned</th>
              <th>{t('source')}</th>
              <th>Response</th>
              <th>{t('actions')}</th>
            </tr>
          </thead>
          <tbody>
            {leads.map(lead => (
              <tr key={lead.id} data-testid={`lead-row-${lead.id}`} style={{ cursor: 'pointer' }} onClick={() => { setSelectedLead(lead); loadTimeline(lead.id); }}>
                <td onClick={e => e.stopPropagation()}>
                  <input type="checkbox" checked={selectedLeads.includes(lead.id)} onChange={() => toggleSelect(lead.id)} data-testid={`select-lead-${lead.id}`} />
                </td>
                <td>
                  <div style={{ fontWeight: 600, fontSize: 11 }}>{lead.name}</div>
                  {lead.email && <div style={{ fontSize: 9, color: '#8896ab' }}>{lead.email}</div>}
                </td>
                <td style={{ fontSize: 11 }}>{lead.phone || '-'}</td>
                <td><StageBadge stage={lead.stage} /></td>
                <td><AssignBadge assignedTo={lead.assigned_to} status={lead.assignment_status} /></td>
                <td style={{ fontSize: 10, color: '#556680', textTransform: 'capitalize' }}>{lead.source?.replace('_', ' ')}</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                    <span style={{ fontSize: 10, fontWeight: 600 }}>{lead.follow_up_count || 0}x</span>
                    <ResponseTimeBadge minutes={lead.response_time_minutes} />
                  </div>
                </td>
                <td onClick={e => e.stopPropagation()}>
                  <div style={{ display: 'flex', gap: 3 }}>
                    {/* Stage-specific actions */}
                    {lead.stage === 'acquisition' && (
                      <button className="btn-pill btn-pill-secondary" style={{ padding: '2px 7px', fontSize: 9 }} onClick={() => transitionStage(lead.id, 'nurturing', 'Initial contact')} data-testid={`contact-${lead.id}`}>
                        <Phone size={9} style={{ display: 'inline', marginRight: 2 }} />Contact
                      </button>
                    )}
                    {lead.stage === 'nurturing' && (
                      <button className="btn-pill btn-pill-secondary" style={{ padding: '2px 7px', fontSize: 9 }} onClick={() => transitionStage(lead.id, 'appointment', 'Schedule survey')} data-testid={`schedule-${lead.id}`}>
                        <Calendar size={9} style={{ display: 'inline', marginRight: 2 }} />Jadwal
                      </button>
                    )}
                    {lead.stage === 'appointment' && (
                      <button className="btn-pill btn-pill-primary" style={{ padding: '2px 7px', fontSize: 9 }} onClick={() => transitionStage(lead.id, 'booking', 'Booking confirmed')} data-testid={`book-${lead.id}`}>
                        <Handshake size={9} style={{ display: 'inline', marginRight: 2 }} />Book
                      </button>
                    )}
                    {lead.stage === 'recycle' && (
                      <button className="btn-pill btn-pill-secondary" style={{ padding: '2px 7px', fontSize: 9, color: '#2563eb' }} onClick={() => transitionStage(lead.id, 'acquisition', 'Re-engage')} data-testid={`reengage-${lead.id}`}>
                        <RefreshCw size={9} style={{ display: 'inline', marginRight: 2 }} />Re-engage
                      </button>
                    )}
                    {/* Accept/Reject for pending assignments */}
                    {lead.assignment_status === 'pending' && lead.assigned_to === user?.email && (
                      <>
                        <button className="btn-pill btn-pill-primary" style={{ padding: '2px 6px', fontSize: 9 }} onClick={() => handleRespondAssignment(lead.id, 'accept')} data-testid={`accept-${lead.id}`}>
                          <Check size={9} />
                        </button>
                        <button className="btn-pill btn-pill-secondary" style={{ padding: '2px 6px', fontSize: 9, color: '#ef4444' }} onClick={() => setShowReject(lead.id)} data-testid={`reject-${lead.id}`}>
                          <XCircle size={9} />
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {leads.length === 0 && !loading && (
          <div style={{ textAlign: 'center', padding: 24, color: '#8896ab', fontSize: 11 }}>{t('no_data')}</div>
        )}
      </div>

      {/* Lead Detail + Timeline Panel */}
      {selectedLead && (
        <div className="glass-card animate-slide-in" style={{ marginTop: 8, padding: 12 }} data-testid="lead-detail-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <h3 style={{ fontSize: 14, fontWeight: 800 }}>{selectedLead.name}</h3>
            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <button className="btn-pill btn-pill-secondary" style={{ fontSize: 9, padding: '2px 8px' }} onClick={() => { loadTimeline(selectedLead.id); setShowTimeline(!showTimeline); }} data-testid="toggle-timeline">
                <History size={10} style={{ display: 'inline', marginRight: 3 }} />{showTimeline ? 'Hide' : 'Show'} Timeline
              </button>
              <button onClick={() => { setSelectedLead(null); setShowTimeline(false); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8896ab', fontSize: 16, fontWeight: 700 }} data-testid="close-detail">x</button>
            </div>
          </div>

          {/* Lead Info Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 8, marginBottom: 8 }}>
            <div><div style={{ fontSize: 8, fontWeight: 700, color: '#8896ab', marginBottom: 1 }}>Stage</div><StageBadge stage={selectedLead.stage} /></div>
            <div><div style={{ fontSize: 8, fontWeight: 700, color: '#8896ab', marginBottom: 1 }}>{t('phone')}</div><div style={{ fontSize: 11 }}>{selectedLead.phone || '-'}</div></div>
            <div><div style={{ fontSize: 8, fontWeight: 700, color: '#8896ab', marginBottom: 1 }}>{t('email')}</div><div style={{ fontSize: 11 }}>{selectedLead.email || '-'}</div></div>
            <div><div style={{ fontSize: 8, fontWeight: 700, color: '#8896ab', marginBottom: 1 }}>{t('source')}</div><div style={{ fontSize: 11, textTransform: 'capitalize' }}>{selectedLead.source?.replace('_', ' ')}</div></div>
            <div><div style={{ fontSize: 8, fontWeight: 700, color: '#8896ab', marginBottom: 1 }}>Follow-up</div><div style={{ fontSize: 11 }}>{selectedLead.follow_up_count || 0}x</div></div>
            <div><div style={{ fontSize: 8, fontWeight: 700, color: '#8896ab', marginBottom: 1 }}>Response Time</div><ResponseTimeBadge minutes={selectedLead.response_time_minutes} /></div>
          </div>

          {/* Stage Transition Buttons */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
            {Object.entries(STAGE_CONFIG).map(([key, cfg]) => (
              <button key={key}
                disabled={selectedLead.stage === key}
                onClick={() => transitionStage(selectedLead.id, key)}
                className="btn-pill"
                style={{
                  padding: '3px 8px', fontSize: 9, fontWeight: 700,
                  background: selectedLead.stage === key ? cfg.color : cfg.bg,
                  color: selectedLead.stage === key ? 'white' : cfg.color,
                  border: 'none', cursor: selectedLead.stage === key ? 'default' : 'pointer',
                  opacity: selectedLead.stage === key ? 1 : 0.8
                }}
                data-testid={`transition-to-${key}`}>
                <cfg.icon size={10} style={{ display: 'inline', marginRight: 3 }} />{cfg.label}
              </button>
            ))}
          </div>

          {selectedLead.notes && <div style={{ fontSize: 10, color: '#556680', background: 'rgba(0,0,0,0.02)', padding: 6, borderRadius: 6, marginBottom: 6 }}>{t('notes')}: {selectedLead.notes}</div>}

          {/* Timeline */}
          {showTimeline && (
            <div style={{ borderTop: '1px solid rgba(0,0,0,0.05)', paddingTop: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 800, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                <Activity size={12} color="#2563eb" /> Timeline
              </div>
              <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                {timeline.length === 0 && <div style={{ fontSize: 10, color: '#8896ab', textAlign: 'center', padding: 10 }}>No timeline events</div>}
                {timeline.map((item, i) => {
                  const iconMap = { event: Zap, activity: MessageCircle, whatsapp: Phone, assignment: UserCheck };
                  const colorMap = { event: '#2563eb', activity: '#10b981', whatsapp: '#25d366', assignment: '#f59e0b' };
                  const Icon = iconMap[item.type] || Activity;
                  const clr = colorMap[item.type] || '#8896ab';
                  return (
                    <div key={i} style={{ display: 'flex', gap: 8, padding: '4px 0', borderBottom: i < timeline.length - 1 ? '1px solid rgba(0,0,0,0.03)' : 'none' }}>
                      <div style={{ width: 20, height: 20, borderRadius: '50%', background: `${clr}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        <Icon size={10} color={clr} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 10, fontWeight: 600, color: '#1a2236' }}>{item.subtype?.replace('.', ' ').replace('_', ' ')}</div>
                        <div style={{ fontSize: 9, color: '#8896ab', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.description}</div>
                      </div>
                      <div style={{ fontSize: 8, color: '#8896ab', flexShrink: 0 }}>{item.created_at ? new Date(item.created_at).toLocaleString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Assign Modal */}
      {showAssign && (
        <div className="modal-overlay" onClick={() => setShowAssign(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="assign-modal">
            <h2 style={{ fontSize: 16, fontWeight: 800, marginBottom: 12 }}>Assign {selectedLeads.length} Lead(s)</h2>
            <div style={{ marginBottom: 10 }}>
              <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#8896ab', marginBottom: 3 }}>Assign to</label>
              <select value={assignTarget} onChange={e => setAssignTarget(e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit' }} data-testid="assign-target-select">
                <option value="">Select user...</option>
                {users.filter(u => u.status === 'active').map(u => (
                  <option key={u.email} value={u.email}>{u.name || u.email} ({u.role})</option>
                ))}
              </select>
            </div>
            <div style={{ marginBottom: 10 }}>
              <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#8896ab', marginBottom: 3 }}>Reason (optional)</label>
              <input value={assignReason} onChange={e => setAssignReason(e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit' }} placeholder="e.g., Nearest location" data-testid="assign-reason-input" />
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn-pill btn-pill-primary" onClick={handleAssign} disabled={!assignTarget} data-testid="confirm-assign-btn" style={{ fontSize: 11 }}>Assign</button>
              <button className="btn-pill btn-pill-secondary" onClick={() => setShowAssign(false)} style={{ fontSize: 11 }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Assignment Modal */}
      {showReject && (
        <div className="modal-overlay" onClick={() => setShowReject(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="reject-modal">
            <h2 style={{ fontSize: 16, fontWeight: 800, marginBottom: 12 }}>Reject Assignment</h2>
            <div style={{ marginBottom: 10 }}>
              <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#8896ab', marginBottom: 3 }}>Reason</label>
              <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit', minHeight: 60 }} placeholder="Alasan penolakan..." data-testid="reject-reason-input" />
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn-pill btn-pill-primary" style={{ background: '#ef4444', fontSize: 11 }} onClick={() => handleRespondAssignment(showReject, 'reject', rejectReason)} data-testid="confirm-reject-btn">Reject</button>
              <button className="btn-pill btn-pill-secondary" onClick={() => setShowReject(null)} style={{ fontSize: 11 }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Lead Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} data-testid="create-lead-modal">
            <h2 style={{ fontSize: 16, fontWeight: 800, marginBottom: 12 }}>Lead Baru</h2>
            <form onSubmit={handleCreate}>
              {[
                { key: 'name', label: t('name'), type: 'text', required: true },
                { key: 'phone', label: t('phone'), type: 'tel' },
                { key: 'email', label: t('email'), type: 'email' },
              ].map(field => (
                <div key={field.key} style={{ marginBottom: 8 }}>
                  <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>{field.label}</label>
                  <input type={field.type} value={form[field.key]} onChange={e => setForm({ ...form, [field.key]: e.target.value })} required={field.required}
                    style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit', outline: 'none' }}
                    data-testid={`lead-form-${field.key}`} />
                </div>
              ))}
              <div style={{ marginBottom: 8 }}>
                <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>{t('source')}</label>
                <select value={form.source} onChange={e => setForm({ ...form, source: e.target.value })}
                  style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit' }} data-testid="lead-form-source">
                  {sources.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                </select>
              </div>
              <div style={{ marginBottom: 8 }}>
                <label style={{ display: 'block', fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>{t('notes')}</label>
                <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })}
                  style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 12, fontFamily: 'inherit', resize: 'vertical', minHeight: 40 }} data-testid="lead-form-notes" />
              </div>
              <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
                <button type="submit" className="btn-pill btn-pill-primary" data-testid="lead-form-submit" style={{ fontSize: 11 }}>{t('save')}</button>
                <button type="button" className="btn-pill btn-pill-secondary" onClick={() => setShowForm(false)} style={{ fontSize: 11 }}>{t('cancel')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
