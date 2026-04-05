import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { Users, Plus, Search, Phone, ArrowRight, Layers, Target, RefreshCw, Calendar, Handshake } from 'lucide-react';

const STAGE_CONFIG = {
  acquisition: { label: 'Akuisisi', color: '#2563eb', bg: 'rgba(37,99,235,0.08)', icon: Target },
  nurturing: { label: 'Nurturing', color: '#f59e0b', bg: 'rgba(245,158,11,0.08)', icon: Phone },
  appointment: { label: 'Appointment', color: '#7c3aed', bg: 'rgba(124,58,237,0.08)', icon: Calendar },
  booking: { label: 'Booking', color: '#10b981', bg: 'rgba(16,185,129,0.08)', icon: Handshake },
  recycle: { label: 'Recycle', color: '#8896ab', bg: 'rgba(148,163,184,0.08)', icon: RefreshCw },
};

export default function CRMPage() {
  const [searchParams] = useSearchParams();
  const [leads, setLeads] = useState([]);
  const [projects, setProjects] = useState([]);
  const [pipeline, setPipeline] = useState(null);
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
  const [form, setForm] = useState({ name: '', phone: '', email: '', source: 'manual', campaign: '', project_id: '', notes: '' });
  const [selectedLead, setSelectedLead] = useState(null);
  const { t } = useLang();

  // Sync filter when URL params change (sidebar navigation)
  useEffect(() => {
    const urlStage = searchParams.get('stage') || '';
    const urlStatus = searchParams.get('status') || '';
    setFilters(prev => ({ ...prev, stage: urlStage, status: urlStatus }));
  }, [searchParams]);

  useEffect(() => { loadProjects(); loadPipeline(); }, []);
  useEffect(() => { loadLeads(); }, [filters]);

  const loadProjects = async () => {
    try { const { data } = await api.get('/projects'); setProjects(data.data); } catch {}
  };

  const loadPipeline = async () => {
    try { const { data } = await api.get('/leads/pipeline'); setPipeline(data.data); } catch {}
  };

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
      loadLeads();
      loadPipeline();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const updateLeadStatus = async (leadId, newStatus) => {
    try {
      await api.put(`/leads/${leadId}`, { status: newStatus });
      loadLeads();
      loadPipeline();
      if (selectedLead?.id === leadId) setSelectedLead({ ...selectedLead, status: newStatus });
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const moveLeadToStage = async (leadId, newStage) => {
    try {
      await api.put(`/leads/${leadId}`, { stage: newStage });
      loadLeads();
      loadPipeline();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const sources = ['meta_ads', 'google_ads', 'tiktok_ads', 'referral', 'walk_in', 'website', 'event', 'manual', 'csv_import'];
  const stages = pipeline?.stages || {};

  return (
    <div className="animate-fade-in" data-testid="crm-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.02em' }}>CRM - Lead Lifecycle</h1>
          <p style={{ color: '#8896ab', fontSize: 11, marginTop: 1 }}>Pipeline lead dengan lifecycle stages</p>
        </div>
        <button className="btn-pill btn-pill-primary" onClick={() => setShowForm(true)} data-testid="add-lead-btn">
          <Plus size={14} style={{ display: 'inline', marginRight: 4 }} />{t('add_new')}
        </button>
      </div>

      {/* Lifecycle Funnel Mini Dashboard */}
      <div className="glass-card" style={{ padding: '10px 14px', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
          <Layers size={14} color="#2563eb" />
          <span style={{ fontSize: 12, fontWeight: 800, color: '#1a2236' }}>Lead Lifecycle</span>
          <span style={{ fontSize: 10, color: '#8896ab', marginLeft: 'auto' }}>{pipeline?.total || total} total</span>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {Object.entries(STAGE_CONFIG).map(([key, cfg]) => {
            const count = stages[key] || 0;
            const isActive = filters.stage === key;
            return (
              <div key={key}
                onClick={() => setFilters({ ...filters, stage: isActive ? '' : key, status: '' })}
                style={{
                  flex: 1, background: isActive ? cfg.color : cfg.bg, borderRadius: 10,
                  padding: '8px 6px', textAlign: 'center', cursor: 'pointer',
                  border: `1px solid ${isActive ? cfg.color : 'transparent'}`,
                  transition: 'all 0.15s ease'
                }}
                data-testid={`stage-${key}`}>
                <cfg.icon size={14} color={isActive ? 'white' : cfg.color} style={{ margin: '0 auto 3px' }} />
                <div style={{ fontSize: 18, fontWeight: 800, color: isActive ? 'white' : cfg.color, lineHeight: 1 }}>{count}</div>
                <div style={{ fontSize: 8, fontWeight: 700, color: isActive ? 'rgba(255,255,255,0.8)' : cfg.color, textTransform: 'uppercase', marginTop: 2 }}>{cfg.label}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Filters Row */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 180 }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#8896ab' }} />
          <input className="sipro-search" placeholder="Cari nama, telepon, email..." value={filters.search} onChange={e => setFilters({ ...filters, search: e.target.value })} data-testid="lead-search" />
        </div>
        <select value={filters.source} onChange={e => setFilters({ ...filters, source: e.target.value })}
          style={{ padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11, fontFamily: 'inherit', background: 'rgba(255,255,255,0.7)' }} data-testid="lead-source-filter">
          <option value="">All Sources</option>
          {sources.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
        <select value={filters.project_id} onChange={e => setFilters({ ...filters, project_id: e.target.value })}
          style={{ padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 11, fontFamily: 'inherit', background: 'rgba(255,255,255,0.7)' }} data-testid="lead-project-filter">
          <option value="">{t('all_projects')}</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        {(filters.stage || filters.status || filters.source || filters.project_id) && (
          <button className="btn-pill btn-pill-secondary" style={{ fontSize: 10, padding: '4px 10px', color: '#ef4444' }}
            onClick={() => setFilters({ stage: '', status: '', source: '', project_id: '', search: filters.search })}>
            Clear Filters
          </button>
        )}
      </div>

      {/* Leads Table */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '8px 14px', borderBottom: '1px solid rgba(0,0,0,0.04)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 12, fontWeight: 700 }}>{total} Leads {filters.stage ? `- Stage: ${STAGE_CONFIG[filters.stage]?.label}` : ''}</span>
        </div>
        <table className="sipro-table" data-testid="leads-table">
          <thead>
            <tr>
              <th>{t('name')}</th>
              <th>{t('phone')}</th>
              <th>Stage</th>
              <th>{t('status')}</th>
              <th>{t('source')}</th>
              <th>Follow-up</th>
              <th>{t('actions')}</th>
            </tr>
          </thead>
          <tbody>
            {leads.map(lead => {
              const sc = STAGE_CONFIG[lead.stage] || STAGE_CONFIG.acquisition;
              return (
                <tr key={lead.id} data-testid={`lead-row-${lead.id}`} style={{ cursor: 'pointer' }} onClick={() => setSelectedLead(lead)}>
                  <td>
                    <div style={{ fontWeight: 600, fontSize: 12 }}>{lead.name}</div>
                    {lead.email && <div style={{ fontSize: 10, color: '#8896ab' }}>{lead.email}</div>}
                  </td>
                  <td style={{ fontSize: 12 }}>{lead.phone || '-'}</td>
                  <td>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, fontWeight: 700, color: sc.color, background: sc.bg, padding: '2px 8px', borderRadius: 6 }}>
                      <sc.icon size={10} />{sc.label}
                    </span>
                  </td>
                  <td><span className={`status-badge status-${lead.status}`}>{lead.status}</span></td>
                  <td style={{ fontSize: 11, color: '#556680', textTransform: 'capitalize' }}>{lead.source?.replace('_', ' ')}</td>
                  <td>
                    <span style={{ fontSize: 11, fontWeight: 600 }}>{lead.follow_up_count || 0}x</span>
                    {lead.last_contacted_at && <div style={{ fontSize: 9, color: '#8896ab' }}>{new Date(lead.last_contacted_at).toLocaleDateString('id-ID')}</div>}
                  </td>
                  <td onClick={e => e.stopPropagation()}>
                    <div style={{ display: 'flex', gap: 3 }}>
                      {lead.stage === 'acquisition' && (
                        <button className="btn-pill btn-pill-secondary" style={{ padding: '2px 8px', fontSize: 10 }} onClick={() => { updateLeadStatus(lead.id, 'contacted'); moveLeadToStage(lead.id, 'nurturing'); }}>
                          <Phone size={10} style={{ display: 'inline', marginRight: 2 }} />Contact
                        </button>
                      )}
                      {lead.stage === 'nurturing' && (
                        <button className="btn-pill btn-pill-secondary" style={{ padding: '2px 8px', fontSize: 10 }} onClick={() => moveLeadToStage(lead.id, 'appointment')}>
                          <ArrowRight size={10} style={{ display: 'inline', marginRight: 2 }} />Jadwal
                        </button>
                      )}
                      {lead.stage === 'appointment' && (
                        <button className="btn-pill btn-pill-primary" style={{ padding: '2px 8px', fontSize: 10 }} onClick={() => moveLeadToStage(lead.id, 'booking')}>
                          <Handshake size={10} style={{ display: 'inline', marginRight: 2 }} />Book
                        </button>
                      )}
                      {lead.stage === 'recycle' && (
                        <button className="btn-pill btn-pill-secondary" style={{ padding: '2px 8px', fontSize: 10, color: '#2563eb' }} onClick={() => moveLeadToStage(lead.id, 'acquisition')}>
                          <RefreshCw size={10} style={{ display: 'inline', marginRight: 2 }} />Re-engage
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {leads.length === 0 && !loading && (
          <div style={{ textAlign: 'center', padding: 30, color: '#8896ab', fontSize: 12 }}>{t('no_data')}</div>
        )}
      </div>

      {/* Lead Detail Panel */}
      {selectedLead && (
        <div className="glass-card animate-slide-in" style={{ marginTop: 10, padding: 14 }} data-testid="lead-detail-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <h3 style={{ fontSize: 16, fontWeight: 800 }}>{selectedLead.name}</h3>
            <button onClick={() => setSelectedLead(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8896ab', fontSize: 18, fontWeight: 700 }}>x</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
            <div><div style={{ fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Stage</div>
              <span style={{ fontSize: 11, fontWeight: 700, color: STAGE_CONFIG[selectedLead.stage]?.color || '#8896ab' }}>{STAGE_CONFIG[selectedLead.stage]?.label || selectedLead.stage}</span>
            </div>
            <div><div style={{ fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>{t('phone')}</div><div style={{ fontSize: 12 }}>{selectedLead.phone || '-'}</div></div>
            <div><div style={{ fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>{t('email')}</div><div style={{ fontSize: 12 }}>{selectedLead.email || '-'}</div></div>
            <div><div style={{ fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>{t('source')}</div><div style={{ fontSize: 12, textTransform: 'capitalize' }}>{selectedLead.source?.replace('_', ' ')}</div></div>
            <div><div style={{ fontSize: 9, fontWeight: 700, color: '#8896ab', marginBottom: 2 }}>Follow-up</div><div style={{ fontSize: 12 }}>{selectedLead.follow_up_count || 0}x</div></div>
          </div>
          {selectedLead.notes && <div style={{ marginTop: 8, fontSize: 11, color: '#556680', background: 'rgba(0,0,0,0.02)', padding: 8, borderRadius: 6 }}>{t('notes')}: {selectedLead.notes}</div>}
        </div>
      )}

      {/* Create Lead Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>Lead Baru</h2>
            <form onSubmit={handleCreate}>
              {[
                { key: 'name', label: t('name'), type: 'text', required: true },
                { key: 'phone', label: t('phone'), type: 'tel' },
                { key: 'email', label: t('email'), type: 'email' },
              ].map(field => (
                <div key={field.key} style={{ marginBottom: 10 }}>
                  <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#8896ab', marginBottom: 3 }}>{field.label}</label>
                  <input type={field.type} value={form[field.key]} onChange={e => setForm({ ...form, [field.key]: e.target.value })} required={field.required}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 13, fontFamily: 'inherit', outline: 'none' }}
                    data-testid={`lead-form-${field.key}`} />
                </div>
              ))}
              <div style={{ marginBottom: 10 }}>
                <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#8896ab', marginBottom: 3 }}>{t('source')}</label>
                <select value={form.source} onChange={e => setForm({ ...form, source: e.target.value })}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 13, fontFamily: 'inherit' }} data-testid="lead-form-source">
                  {sources.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                </select>
              </div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#8896ab', marginBottom: 3 }}>{t('notes')}</label>
                <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.06)', fontSize: 13, fontFamily: 'inherit', resize: 'vertical', minHeight: 50 }} data-testid="lead-form-notes" />
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
                <button type="submit" className="btn-pill btn-pill-primary" data-testid="lead-form-submit">{t('save')}</button>
                <button type="button" className="btn-pill btn-pill-secondary" onClick={() => setShowForm(false)}>{t('cancel')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
