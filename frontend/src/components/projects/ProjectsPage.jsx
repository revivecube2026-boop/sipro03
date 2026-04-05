import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { Building2, Plus, MapPin, Search, ArrowUpRight } from 'lucide-react';

function formatCurrency(num) {
  if (!num) return 'Rp 0';
  if (num >= 1e9) return `Rp ${(num / 1e9).toFixed(1)}M`;
  return `Rp ${num.toLocaleString('id-ID')}`;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', location: '', description: '', total_units: 0, target_revenue: 0, status: 'planning' });
  const { t } = useLang();
  const navigate = useNavigate();

  useEffect(() => { loadProjects(); }, []);

  const loadProjects = async () => {
    try {
      const { data } = await api.get('/projects', { params: search ? { search } : {} });
      setProjects(data.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/projects', form);
      setShowForm(false);
      setForm({ name: '', location: '', description: '', total_units: 0, target_revenue: 0, status: 'planning' });
      loadProjects();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const filtered = projects.filter(p =>
    p.name?.toLowerCase().includes(search.toLowerCase()) ||
    p.location?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="animate-fade-in" data-testid="projects-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em' }}>{t('projects')}</h1>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Kelola semua proyek properti</p>
        </div>
        <button className="btn-pill btn-pill-primary" onClick={() => setShowForm(true)} data-testid="add-project-btn">
          <Plus size={16} style={{ display: 'inline', marginRight: 6 }} />{t('add_new')}
        </button>
      </div>

      {/* Mini Dashboard */}
      <div className="mini-dashboard" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="mini-dashboard-card">
          <div className="kpi-number">{projects.length}</div>
          <div className="kpi-label">{t('total_projects')}</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number">{projects.filter(p => p.status === 'active').length}</div>
          <div className="kpi-label">{t('active')}</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number">{projects.reduce((sum, p) => sum + (p.total_units || 0), 0)}</div>
          <div className="kpi-label">{t('total_units')}</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number" style={{ fontSize: 20 }}>{formatCurrency(projects.reduce((sum, p) => sum + (p.target_revenue || 0), 0))}</div>
          <div className="kpi-label">Target {t('revenue')}</div>
        </div>
      </div>

      {/* Search */}
      <div style={{ position: 'relative', marginBottom: 20 }}>
        <Search size={18} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
        <input className="sipro-search" placeholder={t('search')} value={search} onChange={e => setSearch(e.target.value)} data-testid="project-search" />
      </div>

      {/* Project Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }} className="stagger-children">
        {filtered.map(proj => (
          <div key={proj.id} className="glass-card glass-card-clickable" style={{ padding: 20 }}
            onClick={() => navigate(`/siteplan?project=${proj.id}`)} data-testid={`project-card-${proj.id}`}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#1e293b' }}>{proj.name}</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 4, color: '#64748b', fontSize: 12 }}>
                  <MapPin size={12} /> {proj.location || '-'}
                </div>
              </div>
              <span className={`status-badge status-${proj.status}`}>{proj.status}</span>
            </div>
            {proj.description && <p style={{ fontSize: 13, color: '#64748b', marginBottom: 12, lineHeight: 1.4 }}>{proj.description}</p>}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
              <div style={{ background: '#f8fafc', borderRadius: 10, padding: '8px 12px', textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: '#1e293b' }}>{proj.total_units || 0}</div>
                <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8' }}>{t('total_units')}</div>
              </div>
              <div style={{ background: '#f0fdf4', borderRadius: 10, padding: '8px 12px', textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: '#16a34a' }}>{proj.units_sold || 0}</div>
                <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8' }}>{t('sold')}</div>
              </div>
              <div style={{ background: '#f8fafc', borderRadius: 10, padding: '8px 12px', textAlign: 'center' }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#1e293b' }}>{formatCurrency(proj.target_revenue)}</div>
                <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8' }}>Target</div>
              </div>
            </div>
            <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#2563eb', display: 'flex', alignItems: 'center', gap: 4 }}>
                {t('siteplan')} <ArrowUpRight size={14} />
              </span>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && !loading && (
        <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>{t('no_data')}</div>
      )}

      {/* Create Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Proyek Baru</h2>
            <form onSubmit={handleCreate}>
              {[
                { key: 'name', label: t('project_name'), type: 'text', required: true },
                { key: 'location', label: t('location'), type: 'text' },
                { key: 'description', label: t('description'), type: 'text' },
                { key: 'total_units', label: t('total_units'), type: 'number' },
                { key: 'target_revenue', label: `Target ${t('revenue')}`, type: 'number' },
              ].map(field => (
                <div key={field.key} style={{ marginBottom: 14 }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{field.label}</label>
                  <input
                    type={field.type}
                    value={form[field.key]}
                    onChange={e => setForm({ ...form, [field.key]: field.type === 'number' ? Number(e.target.value) : e.target.value })}
                    required={field.required}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit', outline: 'none' }}
                    data-testid={`project-form-${field.key}`}
                  />
                </div>
              ))}
              <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                <button type="submit" className="btn-pill btn-pill-primary" data-testid="project-form-submit">{t('save')}</button>
                <button type="button" className="btn-pill btn-pill-secondary" onClick={() => setShowForm(false)}>{t('cancel')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
