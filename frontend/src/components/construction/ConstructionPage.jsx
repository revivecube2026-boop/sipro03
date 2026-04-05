import React, { useState, useEffect } from 'react';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { HardHat, ChevronDown, ChevronUp, CheckCircle, Clock, AlertTriangle, Circle, Shield } from 'lucide-react';

export default function ConstructionPage() {
  const [summary, setSummary] = useState(null);
  const [units, setUnits] = useState([]);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [expandedUnit, setExpandedUnit] = useState(null);
  const [loading, setLoading] = useState(true);
  const { t } = useLang();

  useEffect(() => { loadProjects(); }, []);
  useEffect(() => { loadData(); }, [selectedProject]);

  const loadProjects = async () => {
    try { const { data } = await api.get('/projects'); setProjects(data.data); } catch {}
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const params = selectedProject ? { project_id: selectedProject } : {};
      const [sumRes, unitsRes] = await Promise.all([
        api.get('/construction/summary', { params }),
        api.get('/construction/units', { params })
      ]);
      setSummary(sumRes.data.data);
      setUnits(unitsRes.data.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const updateTaskStatus = async (unitId, phaseId, taskId, newStatus) => {
    try {
      await api.put(`/construction/units/${unitId}/progress`, {
        phase_id: phaseId,
        task_id: taskId,
        status: newStatus,
        notes: `Status updated to ${newStatus}`
      });
      loadData();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const taskStatusIcon = (status) => {
    if (status === 'completed' || status === 'passed') return <CheckCircle size={16} color="#22c55e" />;
    if (status === 'in_progress' || status === 'qc_pending') return <Clock size={16} color="#3b82f6" />;
    if (status === 'failed' || status === 'rework') return <AlertTriangle size={16} color="#ef4444" />;
    return <Circle size={16} color="#cbd5e1" />;
  };

  const s = summary || {};

  return (
    <div className="animate-fade-in" data-testid="construction-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em' }}>
            <HardHat size={24} style={{ display: 'inline', marginRight: 8, color: '#f59e0b' }} />Konstruksi
          </h1>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Progress pembangunan dan QC</p>
        </div>
        <select value={selectedProject} onChange={e => setSelectedProject(e.target.value)}
          style={{ padding: '10px 16px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13, fontFamily: 'inherit', background: 'white' }} data-testid="construction-project-select">
          <option value="">{t('all_projects')}</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      {/* Mini Dashboard */}
      <div className="mini-dashboard" style={{ gridTemplateColumns: 'repeat(6, 1fr)' }}>
        <div className="mini-dashboard-card">
          <div className="kpi-number">{s.total || 0}</div>
          <div className="kpi-label">{t('total')}</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number" style={{ color: '#94a3b8' }}>{s.not_started || 0}</div>
          <div className="kpi-label">Belum Mulai</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number" style={{ color: '#3b82f6' }}>{s.in_progress || 0}</div>
          <div className="kpi-label">Berjalan</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number" style={{ color: '#22c55e' }}>{s.completed || 0}</div>
          <div className="kpi-label">{t('completed')}</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number" style={{ color: '#ef4444' }}>{s.qc_hold || 0}</div>
          <div className="kpi-label">QC Hold</div>
        </div>
        <div className="mini-dashboard-card" style={{ background: 'linear-gradient(135deg, rgba(37,99,235,0.08), rgba(37,99,235,0.02))' }}>
          <div className="kpi-number" style={{ color: '#2563eb' }}>{s.avg_progress || 0}%</div>
          <div className="kpi-label">Rata-rata</div>
        </div>
      </div>

      {/* Construction Units List */}
      <div className="stagger-children">
        {units.map(cu => (
          <div key={cu.id} className="glass-card" style={{ marginBottom: 12, overflow: 'hidden' }}>
            {/* Unit Header */}
            <div
              style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', background: expandedUnit === cu.unit_id ? 'rgba(37,99,235,0.03)' : 'transparent' }}
              onClick={() => setExpandedUnit(expandedUnit === cu.unit_id ? null : cu.unit_id)}
              data-testid={`construction-unit-${cu.unit_label}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{
                  width: 48, height: 48, borderRadius: 12,
                  background: cu.overall_status === 'completed' ? '#d1fae5' : cu.overall_status === 'qc_hold' ? '#fef3c7' : '#dbeafe',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 14,
                  color: cu.overall_status === 'completed' ? '#065f46' : cu.overall_status === 'qc_hold' ? '#92400e' : '#1e40af'
                }}>
                  {cu.unit_label}
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>Unit {cu.unit_label}</div>
                  <span className={`status-badge status-${cu.overall_status}`} style={{ marginTop: 2 }}>
                    {cu.overall_status?.replace('_', ' ')}
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                <div style={{ width: 120 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: '#94a3b8' }}>Progress</span>
                    <span style={{ fontSize: 13, fontWeight: 800, color: '#2563eb' }}>{cu.overall_progress}%</span>
                  </div>
                  <div className="progress-bar" style={{ height: 8, borderRadius: 4 }}>
                    <div className="progress-bar-fill" style={{
                      width: `${cu.overall_progress}%`,
                      background: cu.overall_progress >= 80 ? '#22c55e' : cu.overall_progress >= 40 ? '#3b82f6' : '#f59e0b',
                      borderRadius: 4
                    }} />
                  </div>
                </div>
                {expandedUnit === cu.unit_id ? <ChevronUp size={20} color="#94a3b8" /> : <ChevronDown size={20} color="#94a3b8" />}
              </div>
            </div>

            {/* Expanded Phases */}
            {expandedUnit === cu.unit_id && (
              <div style={{ padding: '0 20px 20px' }} className="animate-fade-in">
                {(cu.phases || []).map(phase => (
                  <div key={phase.id} style={{ marginBottom: 12, background: '#f8fafc', borderRadius: 12, padding: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {taskStatusIcon(phase.status)}
                        <span style={{ fontWeight: 700, fontSize: 13 }}>{phase.name}</span>
                        <span style={{ fontSize: 11, color: '#94a3b8' }}>({phase.weight}%)</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="progress-bar" style={{ width: 60, height: 6 }}>
                          <div className="progress-bar-fill" style={{ width: `${phase.progress || 0}%`, background: '#3b82f6' }} />
                        </div>
                        <span style={{ fontSize: 12, fontWeight: 700 }}>{phase.progress || 0}%</span>
                      </div>
                    </div>
                    {/* Tasks */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {(phase.tasks || []).map(task => (
                        <div key={task.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 12px', background: 'white', borderRadius: 8, border: '1px solid #f1f5f9' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            {taskStatusIcon(task.status)}
                            <span style={{ fontSize: 13, fontWeight: 500 }}>{task.name}</span>
                            <span style={{ fontSize: 10, color: '#94a3b8' }}>({task.weight}%)</span>
                          </div>
                          <div style={{ display: 'flex', gap: 4 }}>
                            {task.status === 'not_started' && (
                              <button className="btn-pill btn-pill-secondary" style={{ padding: '3px 10px', fontSize: 10 }}
                                onClick={(e) => { e.stopPropagation(); updateTaskStatus(cu.unit_id, phase.id, task.id, 'in_progress'); }}>
                                Mulai
                              </button>
                            )}
                            {task.status === 'in_progress' && (
                              <button className="btn-pill btn-pill-primary" style={{ padding: '3px 10px', fontSize: 10 }}
                                onClick={(e) => { e.stopPropagation(); updateTaskStatus(cu.unit_id, phase.id, task.id, 'completed'); }}>
                                <CheckCircle size={10} style={{ display: 'inline', marginRight: 3 }} />Selesai
                              </button>
                            )}
                            {task.status === 'failed' && (
                              <button className="btn-pill btn-pill-secondary" style={{ padding: '3px 10px', fontSize: 10, color: '#f59e0b' }}
                                onClick={(e) => { e.stopPropagation(); updateTaskStatus(cu.unit_id, phase.id, task.id, 'in_progress'); }}>
                                Rework
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}

                {/* QC Results */}
                {cu.qc_results && cu.qc_results.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Shield size={14} color="#7c3aed" /> QC Results
                    </h4>
                    {cu.qc_results.map(qc => (
                      <div key={qc.id} style={{ fontSize: 12, padding: '4px 0', color: '#64748b' }}>
                        {qc.result === 'pass' ? <CheckCircle size={12} color="#22c55e" style={{ display: 'inline', marginRight: 4 }} /> : <AlertTriangle size={12} color="#ef4444" style={{ display: 'inline', marginRight: 4 }} />}
                        {qc.result.toUpperCase()} - {qc.notes || 'No notes'} ({new Date(qc.created_at).toLocaleDateString('id-ID')})
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {units.length === 0 && !loading && (
        <div className="glass-card" style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>
          <HardHat size={48} style={{ marginBottom: 12 }} />
          <p>Belum ada data konstruksi. Mulai tracking dari halaman unit.</p>
        </div>
      )}
    </div>
  );
}
