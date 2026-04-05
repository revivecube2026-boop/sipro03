import React, { useState, useEffect } from 'react';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { Search, Grid3X3, Filter } from 'lucide-react';

function formatCurrency(num) {
  if (!num) return 'Rp 0';
  return `Rp ${num.toLocaleString('id-ID')}`;
}

export default function UnitsPage() {
  const [units, setUnits] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({ project_id: '', status: '', block: '', search: '' });
  const { t } = useLang();

  useEffect(() => { loadProjects(); }, []);
  useEffect(() => { loadUnits(); }, [filters]);

  const loadProjects = async () => {
    try {
      const { data } = await api.get('/projects');
      setProjects(data.data);
    } catch {}
  };

  const loadUnits = async () => {
    setLoading(true);
    try {
      const params = {};
      Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
      const { data } = await api.get('/units', { params });
      setUnits(data.data);
      setTotal(data.total);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const statusFilter = ['', 'available', 'reserved', 'booked', 'sold'];
  const summary = {
    total,
    available: units.filter(u => u.status === 'available').length,
    reserved: units.filter(u => u.status === 'reserved').length,
    booked: units.filter(u => u.status === 'booked').length,
    sold: units.filter(u => u.status === 'sold').length,
  };

  return (
    <div className="animate-fade-in" data-testid="units-page">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em' }}>{t('units')}</h1>
        <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Kelola semua unit properti</p>
      </div>

      {/* Mini Dashboard */}
      <div className="mini-dashboard" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
        {[
          { label: t('total'), value: total, color: '#1e293b' },
          { label: t('available'), value: summary.available, color: '#94a3b8' },
          { label: t('reserved'), value: summary.reserved, color: '#f59e0b' },
          { label: t('booked'), value: summary.booked, color: '#f97316' },
          { label: t('sold'), value: summary.sold, color: '#22c55e' },
        ].map((item, i) => (
          <div key={i} className="mini-dashboard-card" onClick={() => setFilters({ ...filters, status: i === 0 ? '' : item.label.toLowerCase() })}>
            <div className="kpi-number" style={{ color: item.color }}>{item.value}</div>
            <div className="kpi-label">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search size={18} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
          <input className="sipro-search" placeholder={t('search')} value={filters.search} onChange={e => setFilters({ ...filters, search: e.target.value })} data-testid="unit-search" />
        </div>
        <select value={filters.project_id} onChange={e => setFilters({ ...filters, project_id: e.target.value })}
          style={{ padding: '10px 14px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13, fontFamily: 'inherit', background: 'white', cursor: 'pointer' }} data-testid="unit-project-filter">
          <option value="">{t('all_projects')}</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <div style={{ display: 'flex', gap: 6 }}>
          {statusFilter.map(s => (
            <button key={s} className={`filter-chip ${filters.status === s ? 'active' : ''}`}
              onClick={() => setFilters({ ...filters, status: s })} data-testid={`unit-status-${s || 'all'}`}>
              {s ? t(s) : t('all_statuses')}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        <table className="sipro-table" data-testid="units-table">
          <thead>
            <tr>
              <th>Label</th>
              <th>{t('block')}</th>
              <th>{t('type')}</th>
              <th>LT/LB</th>
              <th>{t('price')}</th>
              <th>{t('status')}</th>
              <th>Konstruksi</th>
            </tr>
          </thead>
          <tbody>
            {units.map(unit => (
              <tr key={unit.id} data-testid={`unit-row-${unit.id}`}>
                <td style={{ fontWeight: 600 }}>{unit.label}</td>
                <td>{unit.block}</td>
                <td>{unit.unit_type}</td>
                <td>{unit.land_area}/{unit.floor_area} m2</td>
                <td style={{ fontWeight: 600 }}>{formatCurrency(unit.price)}</td>
                <td><span className={`status-badge status-${unit.status}`}>{unit.status}</span></td>
                <td><span className={`status-badge status-${unit.construction_status}`}>{unit.construction_status?.replace('_', ' ')}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {units.length === 0 && !loading && (
          <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>{t('no_data')}</div>
        )}
      </div>
    </div>
  );
}
