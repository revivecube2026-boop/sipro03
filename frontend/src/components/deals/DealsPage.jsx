import React, { useState, useEffect } from 'react';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { Handshake, Plus, Search, ArrowRight } from 'lucide-react';

function formatCurrency(num) {
  if (!num) return 'Rp 0';
  return `Rp ${num.toLocaleString('id-ID')}`;
}

export default function DealsPage() {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({ status: '', project_id: '', search: '' });
  const [projects, setProjects] = useState([]);
  const { t } = useLang();

  useEffect(() => { loadProjects(); }, []);
  useEffect(() => { loadDeals(); }, [filters]);

  const loadProjects = async () => {
    try { const { data } = await api.get('/projects'); setProjects(data.data); } catch {}
  };

  const loadDeals = async () => {
    setLoading(true);
    try {
      const params = {};
      Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
      const { data } = await api.get('/deals', { params });
      setDeals(data.data);
      setTotal(data.total);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const updateDealStatus = async (dealId, action) => {
    try {
      if (action === 'reserve') await api.post(`/deals/${dealId}/reserve`);
      else if (action === 'booking') await api.post(`/deals/${dealId}/booking`);
      else await api.put(`/deals/${dealId}`, { status: action });
      loadDeals();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
  };

  const statuses = ['draft', 'reserved', 'booked', 'active', 'completed', 'canceled'];
  const statusCounts = {};
  statuses.forEach(s => { statusCounts[s] = deals.filter(d => d.status === s).length; });

  return (
    <div className="animate-fade-in" data-testid="deals-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em' }}>{t('deals')}</h1>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Pipeline deal dan transaksi</p>
        </div>
      </div>

      {/* Mini Dashboard */}
      <div className="mini-dashboard" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))' }}>
        <div className="mini-dashboard-card glass-card-clickable" onClick={() => setFilters({ ...filters, status: '' })}>
          <div className="kpi-number">{total}</div>
          <div className="kpi-label">{t('total')}</div>
        </div>
        {statuses.slice(0, 5).map(s => (
          <div key={s} className="mini-dashboard-card glass-card-clickable" onClick={() => setFilters({ ...filters, status: s })}>
            <div className="kpi-number">{statusCounts[s] || 0}</div>
            <div className="kpi-label">{t(s)}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search size={18} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
          <input className="sipro-search" placeholder={t('search')} value={filters.search} onChange={e => setFilters({ ...filters, search: e.target.value })} data-testid="deal-search" />
        </div>
        <select value={filters.project_id} onChange={e => setFilters({ ...filters, project_id: e.target.value })}
          style={{ padding: '10px 14px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13, fontFamily: 'inherit', background: 'white' }}>
          <option value="">{t('all_projects')}</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className={`filter-chip ${filters.status === '' ? 'active' : ''}`} onClick={() => setFilters({ ...filters, status: '' })}>{t('all_statuses')}</button>
          {statuses.map(s => (
            <button key={s} className={`filter-chip ${filters.status === s ? 'active' : ''}`}
              onClick={() => setFilters({ ...filters, status: s })}>
              {t(s)}
            </button>
          ))}
        </div>
      </div>

      {/* Deals Table */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        <table className="sipro-table" data-testid="deals-table">
          <thead>
            <tr>
              <th>{t('customer')}</th>
              <th>{t('unit')}</th>
              <th>{t('price')}</th>
              <th>{t('payment_method')}</th>
              <th>{t('status')}</th>
              <th>{t('actions')}</th>
            </tr>
          </thead>
          <tbody>
            {deals.map(deal => (
              <tr key={deal.id} data-testid={`deal-row-${deal.id}`}>
                <td>
                  <div style={{ fontWeight: 600 }}>{deal.customer_name}</div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>{deal.customer_phone || deal.customer_email || '-'}</div>
                </td>
                <td style={{ fontWeight: 600 }}>{deal.unit_label || '-'}</td>
                <td style={{ fontWeight: 700 }}>{formatCurrency(deal.price)}</td>
                <td><span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase' }}>{deal.payment_method}</span></td>
                <td><span className={`status-badge status-${deal.status}`}>{deal.status}</span></td>
                <td>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {deal.status === 'draft' && (
                      <button className="btn-pill btn-pill-secondary" style={{ padding: '4px 10px', fontSize: 11 }}
                        onClick={() => updateDealStatus(deal.id, 'reserve')} data-testid={`deal-reserve-${deal.id}`}>
                        Reserve <ArrowRight size={12} style={{ display: 'inline', marginLeft: 2 }} />
                      </button>
                    )}
                    {deal.status === 'reserved' && (
                      <button className="btn-pill btn-pill-primary" style={{ padding: '4px 10px', fontSize: 11 }}
                        onClick={() => updateDealStatus(deal.id, 'booking')} data-testid={`deal-book-${deal.id}`}>
                        Booking <ArrowRight size={12} style={{ display: 'inline', marginLeft: 2 }} />
                      </button>
                    )}
                    {deal.status === 'booked' && (
                      <button className="btn-pill btn-pill-primary" style={{ padding: '4px 10px', fontSize: 11 }}
                        onClick={() => updateDealStatus(deal.id, 'active')}>
                        Activate
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {deals.length === 0 && !loading && (
          <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>{t('no_data')}</div>
        )}
      </div>
    </div>
  );
}
