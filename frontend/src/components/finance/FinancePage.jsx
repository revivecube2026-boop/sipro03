import React, { useState, useEffect } from 'react';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { DollarSign, CreditCard, AlertTriangle, CheckCircle, Search, TrendingUp } from 'lucide-react';

function formatCurrency(num) {
  if (!num) return 'Rp 0';
  if (num >= 1e9) return `Rp ${(num / 1e9).toFixed(1)}M`;
  if (num >= 1e6) return `Rp ${(num / 1e6).toFixed(0)}Jt`;
  return `Rp ${num.toLocaleString('id-ID')}`;
}

export default function FinancePage() {
  const [summary, setSummary] = useState(null);
  const [billings, setBillings] = useState([]);
  const [payments, setPayments] = useState([]);
  const [activeTab, setActiveTab] = useState('billing');
  const [loading, setLoading] = useState(true);
  const { t } = useLang();

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [sumRes, billRes, payRes] = await Promise.all([
        api.get('/finance/summary'),
        api.get('/finance/billing'),
        api.get('/finance/payments')
      ]);
      setSummary(sumRes.data.data);
      setBillings(billRes.data.data);
      setPayments(payRes.data.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const s = summary || {};

  return (
    <div className="animate-fade-in" data-testid="finance-page">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em' }}>
          <DollarSign size={24} style={{ display: 'inline', marginRight: 8, color: '#2563eb' }} />Finance
        </h1>
        <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Billing, pembayaran, dan collection</p>
      </div>

      {/* Mini Dashboard */}
      <div className="mini-dashboard" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
        <div className="mini-dashboard-card" style={{ borderLeft: '4px solid #2563eb' }}>
          <div className="kpi-number" style={{ fontSize: 20 }}>{formatCurrency(s.total_amount)}</div>
          <div className="kpi-label">Total Tagihan</div>
        </div>
        <div className="mini-dashboard-card" style={{ borderLeft: '4px solid #22c55e' }}>
          <div className="kpi-number" style={{ fontSize: 20, color: '#22c55e' }}>{formatCurrency(s.paid_amount)}</div>
          <div className="kpi-label">Terbayar</div>
        </div>
        <div className="mini-dashboard-card" style={{ borderLeft: '4px solid #f59e0b' }}>
          <div className="kpi-number" style={{ fontSize: 20, color: '#f59e0b' }}>{formatCurrency(s.outstanding)}</div>
          <div className="kpi-label">Outstanding</div>
        </div>
        <div className="mini-dashboard-card" style={{ borderLeft: '4px solid #ef4444' }}>
          <div className="kpi-number" style={{ color: '#ef4444' }}>{s.overdue_items || 0}</div>
          <div className="kpi-label">Overdue</div>
        </div>
        <div className="mini-dashboard-card">
          <div className="kpi-number">{s.total_payments || 0}</div>
          <div className="kpi-label">Total Transaksi</div>
        </div>
      </div>

      {/* Collection Progress */}
      {s.total_amount > 0 && (
        <div className="glass-card" style={{ padding: 20, marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontWeight: 700, fontSize: 14 }}>Collection Rate</span>
            <span style={{ fontWeight: 800, fontSize: 18, color: '#2563eb' }}>
              {Math.round((s.paid_amount / s.total_amount) * 100)}%
            </span>
          </div>
          <div className="progress-bar" style={{ height: 10, borderRadius: 5 }}>
            <div className="progress-bar-fill" style={{ width: `${(s.paid_amount / s.total_amount) * 100}%`, background: 'linear-gradient(90deg, #22c55e, #2563eb)', borderRadius: 5 }} />
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button className={`filter-chip ${activeTab === 'billing' ? 'active' : ''}`} onClick={() => setActiveTab('billing')} data-testid="finance-tab-billing">
          <CreditCard size={14} /> Billing Schedule ({billings.length})
        </button>
        <button className={`filter-chip ${activeTab === 'payments' ? 'active' : ''}`} onClick={() => setActiveTab('payments')} data-testid="finance-tab-payments">
          <CheckCircle size={14} /> Riwayat Pembayaran ({payments.length})
        </button>
      </div>

      {/* Billing Table */}
      {activeTab === 'billing' && (
        <div className="glass-card" style={{ overflow: 'hidden' }}>
          {billings.map(bill => (
            <div key={bill.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
              <div style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(241,245,249,0.4)' }}>
                <div>
                  <span style={{ fontWeight: 700, fontSize: 14 }}>{bill.customer_name}</span>
                  <span style={{ fontSize: 12, color: '#94a3b8', marginLeft: 12 }}>Unit: {bill.unit_id}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 12, color: '#94a3b8' }}>Terbayar</div>
                    <div style={{ fontWeight: 700, color: '#22c55e', fontSize: 13 }}>{formatCurrency(bill.paid_amount)}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 12, color: '#94a3b8' }}>Outstanding</div>
                    <div style={{ fontWeight: 700, color: '#f59e0b', fontSize: 13 }}>{formatCurrency(bill.outstanding)}</div>
                  </div>
                </div>
              </div>
              <table className="sipro-table">
                <thead>
                  <tr>
                    <th>Deskripsi</th>
                    <th>Jumlah</th>
                    <th>Jatuh Tempo</th>
                    <th>Terbayar</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(bill.items || []).map(item => {
                    const isOverdue = item.status === 'pending' && item.due_date && new Date(item.due_date) < new Date();
                    return (
                      <tr key={item.id}>
                        <td style={{ fontWeight: 500 }}>{item.description}</td>
                        <td style={{ fontWeight: 600 }}>{formatCurrency(item.amount)}</td>
                        <td>
                          <span style={{ color: isOverdue ? '#ef4444' : '#64748b', fontSize: 13, fontWeight: isOverdue ? 600 : 400 }}>
                            {item.due_date ? new Date(item.due_date).toLocaleDateString('id-ID') : '-'}
                            {isOverdue && <AlertTriangle size={12} style={{ display: 'inline', marginLeft: 4 }} />}
                          </span>
                        </td>
                        <td style={{ fontWeight: 600, color: item.paid_amount > 0 ? '#22c55e' : '#94a3b8' }}>
                          {formatCurrency(item.paid_amount)}
                        </td>
                        <td>
                          <span className={`status-badge ${isOverdue ? 'status-failed' : `status-${item.status === 'paid' ? 'completed' : item.status === 'partial' ? 'in_progress' : 'not_started'}`}`}>
                            {isOverdue ? 'overdue' : item.status}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ))}
          {billings.length === 0 && <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>{t('no_data')}</div>}
        </div>
      )}

      {/* Payments Table */}
      {activeTab === 'payments' && (
        <div className="glass-card" style={{ overflow: 'hidden' }}>
          <table className="sipro-table" data-testid="payments-table">
            <thead>
              <tr>
                <th>Tanggal</th>
                <th>Deal ID</th>
                <th>Jumlah</th>
                <th>Metode</th>
                <th>Referensi</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {payments.map(pay => (
                <tr key={pay.id}>
                  <td style={{ fontSize: 13 }}>{new Date(pay.payment_date).toLocaleDateString('id-ID')}</td>
                  <td style={{ fontSize: 12, color: '#64748b' }}>{pay.deal_id}</td>
                  <td style={{ fontWeight: 700 }}>{formatCurrency(pay.amount)}</td>
                  <td><span style={{ fontSize: 12, textTransform: 'capitalize' }}>{pay.payment_method}</span></td>
                  <td style={{ fontSize: 12, color: '#64748b', fontFamily: 'monospace' }}>{pay.reference || '-'}</td>
                  <td><span className="status-badge status-completed">{pay.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          {payments.length === 0 && <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>{t('no_data')}</div>}
        </div>
      )}
    </div>
  );
}
