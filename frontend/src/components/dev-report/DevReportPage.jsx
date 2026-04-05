import React, { useState, useEffect } from 'react';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { FileText, Plus, CheckCircle, Clock, Circle, AlertTriangle, Edit2, Trash2 } from 'lucide-react';

export default function DevReportPage() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState({ module: '', feature: '', status: 'not_started', priority: 'medium', notes: '', milestone: '', blockers: '' });
  const { t } = useLang();

  useEffect(() => { loadReport(); }, []);

  const loadReport = async () => {
    try {
      const { data } = await api.get('/dev-report');
      setReport(data.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      if (editItem) {
        await api.put(`/dev-report/items/${editItem.id}`, form);
      } else {
        await api.post('/dev-report/items', form);
      }
      setShowForm(false);
      setEditItem(null);
      setForm({ module: '', feature: '', status: 'not_started', priority: 'medium', notes: '', milestone: '', blockers: '' });
      loadReport();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t('confirm_delete'))) return;
    try {
      await api.delete(`/dev-report/items/${id}`);
      loadReport();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const startEdit = (item) => {
    setEditItem(item);
    setForm({ module: item.module, feature: item.feature, status: item.status, priority: item.priority, notes: item.notes || '', milestone: item.milestone || '', blockers: item.blockers || '' });
    setShowForm(true);
  };

  const summary = report?.summary || {};
  const items = report?.items || [];

  // Group by module
  const modules = {};
  items.forEach(item => {
    if (!modules[item.module]) modules[item.module] = [];
    modules[item.module].push(item);
  });

  const statusIcon = (status) => {
    if (status === 'completed') return <CheckCircle size={16} color="#22c55e" />;
    if (status === 'in_progress') return <Clock size={16} color="#3b82f6" />;
    return <Circle size={16} color="#94a3b8" />;
  };

  const priorityColor = { high: '#ef4444', medium: '#f59e0b', low: '#94a3b8' };
  const progressPct = summary.total > 0 ? Math.round((summary.completed / summary.total) * 100) : 0;

  return (
    <div className="animate-fade-in" data-testid="dev-report-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em' }}>
            <FileText size={24} style={{ display: 'inline', marginRight: 8 }} />{t('development_report')}
          </h1>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Tracking progress pengembangan sistem</p>
        </div>
        <button className="btn-pill btn-pill-primary" onClick={() => { setEditItem(null); setForm({ module: '', feature: '', status: 'not_started', priority: 'medium', notes: '', milestone: '', blockers: '' }); setShowForm(true); }} data-testid="add-dev-item-btn">
          <Plus size={16} style={{ display: 'inline', marginRight: 6 }} />{t('add_new')}
        </button>
      </div>

      {/* Summary Cards */}
      <div className="mini-dashboard" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="mini-dashboard-card" style={{ background: 'linear-gradient(135deg, rgba(37,99,235,0.08), rgba(37,99,235,0.02))' }}>
          <div className="kpi-number">{summary.total || 0}</div>
          <div className="kpi-label">Total Fitur</div>
        </div>
        <div className="mini-dashboard-card" style={{ background: 'linear-gradient(135deg, rgba(34,197,94,0.08), rgba(34,197,94,0.02))' }}>
          <div className="kpi-number" style={{ color: '#22c55e' }}>{summary.completed || 0}</div>
          <div className="kpi-label">{t('completed')}</div>
        </div>
        <div className="mini-dashboard-card" style={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.08), rgba(59,130,246,0.02))' }}>
          <div className="kpi-number" style={{ color: '#3b82f6' }}>{summary.in_progress || 0}</div>
          <div className="kpi-label">{t('in_progress')}</div>
        </div>
        <div className="mini-dashboard-card" style={{ background: 'linear-gradient(135deg, rgba(148,163,184,0.08), rgba(148,163,184,0.02))' }}>
          <div className="kpi-number" style={{ color: '#94a3b8' }}>{summary.not_started || 0}</div>
          <div className="kpi-label">{t('not_started')}</div>
        </div>
      </div>

      {/* Overall Progress */}
      <div className="glass-card" style={{ padding: 20, marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ fontWeight: 700, fontSize: 14 }}>Overall Progress</span>
          <span style={{ fontWeight: 800, fontSize: 20, color: '#2563eb' }}>{progressPct}%</span>
        </div>
        <div className="progress-bar" style={{ height: 10, borderRadius: 5 }}>
          <div className="progress-bar-fill" style={{ width: `${progressPct}%`, background: 'linear-gradient(90deg, #2563eb, #22c55e)', borderRadius: 5 }} />
        </div>
      </div>

      {/* Items by Module */}
      {Object.entries(modules).sort().map(([moduleName, moduleItems]) => (
        <div key={moduleName} className="glass-card" style={{ marginBottom: 16, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', background: 'rgba(241,245,249,0.6)', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 700, fontSize: 14 }}>{moduleName}</span>
            <div style={{ display: 'flex', gap: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: '#22c55e' }}>{moduleItems.filter(i => i.status === 'completed').length} selesai</span>
              <span style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8' }}>/ {moduleItems.length} total</span>
            </div>
          </div>
          <table className="sipro-table">
            <tbody>
              {moduleItems.map(item => (
                <tr key={item.id}>
                  <td style={{ width: 30 }}>{statusIcon(item.status)}</td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{item.feature}</div>
                    {item.notes && <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{item.notes}</div>}
                    {item.blockers && (
                      <div style={{ fontSize: 11, color: '#ef4444', marginTop: 2, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <AlertTriangle size={10} /> {item.blockers}
                      </div>
                    )}
                  </td>
                  <td style={{ width: 80 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: priorityColor[item.priority] || '#94a3b8', textTransform: 'uppercase' }}>{item.priority}</span>
                  </td>
                  <td style={{ width: 100 }}>
                    <span className={`status-badge status-${item.status}`}>{t(item.status)}</span>
                  </td>
                  <td style={{ width: 80 }}>
                    <span style={{ fontSize: 11, color: '#94a3b8' }}>{item.milestone || '-'}</span>
                  </td>
                  <td style={{ width: 60 }}>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button onClick={() => startEdit(item)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#3b82f6', padding: 4 }} data-testid={`edit-dev-${item.id}`}>
                        <Edit2 size={14} />
                      </button>
                      <button onClick={() => handleDelete(item.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', padding: 4 }}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {items.length === 0 && !loading && (
        <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>{t('no_data')}</div>
      )}

      {/* Form Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>
              {editItem ? 'Edit Item' : 'Item Baru'}
            </h2>
            <form onSubmit={handleSave}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('module')} *</label>
                  <input value={form.module} onChange={e => setForm({ ...form, module: e.target.value })} required
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="dev-form-module" />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('feature')} *</label>
                  <input value={form.feature} onChange={e => setForm({ ...form, feature: e.target.value })} required
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="dev-form-feature" />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('status')}</label>
                  <select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="dev-form-status">
                    <option value="not_started">{t('not_started')}</option>
                    <option value="in_progress">{t('in_progress')}</option>
                    <option value="completed">{t('completed')}</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('priority')}</label>
                  <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="dev-form-priority">
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>
              <div style={{ marginTop: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('milestone')}</label>
                <input value={form.milestone} onChange={e => setForm({ ...form, milestone: e.target.value })}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="dev-form-milestone" />
              </div>
              <div style={{ marginTop: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('notes')}</label>
                <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit', resize: 'vertical', minHeight: 60 }} data-testid="dev-form-notes" />
              </div>
              <div style={{ marginTop: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('blockers')}</label>
                <input value={form.blockers} onChange={e => setForm({ ...form, blockers: e.target.value })}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="dev-form-blockers" />
              </div>
              <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                <button type="submit" className="btn-pill btn-pill-primary" data-testid="dev-form-submit">{t('save')}</button>
                <button type="button" className="btn-pill btn-pill-secondary" onClick={() => setShowForm(false)}>{t('cancel')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
