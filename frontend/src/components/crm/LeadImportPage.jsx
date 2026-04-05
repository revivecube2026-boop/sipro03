import React, { useState, useRef } from 'react';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { Upload, FileText, CheckCircle, AlertCircle, Download } from 'lucide-react';

export default function LeadImportPage() {
  const [importMode, setImportMode] = useState('csv');
  const [csvData, setCsvData] = useState('');
  const [adsData, setAdsData] = useState({ source: 'meta_ads', campaign: '', leads: [] });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [manualLeads, setManualLeads] = useState([{ name: '', phone: '', email: '', notes: '' }]);
  const fileRef = useRef(null);
  const { t } = useLang();

  const handleCSVUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      const text = evt.target.result;
      setCsvData(text);
      const lines = text.split('\n').filter(l => l.trim());
      if (lines.length > 1) {
        const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
        const parsed = [];
        for (let i = 1; i < lines.length; i++) {
          const vals = lines[i].split(',').map(v => v.trim());
          const lead = {};
          headers.forEach((h, idx) => { lead[h] = vals[idx] || ''; });
          if (lead.name || lead.nama) {
            parsed.push({
              name: lead.name || lead.nama || '',
              phone: lead.phone || lead.telepon || lead.hp || '',
              email: lead.email || '',
              notes: lead.notes || lead.catatan || '',
              ad_set: lead.ad_set || lead.adset || '',
              ad_name: lead.ad_name || '',
            });
          }
        }
        setManualLeads(parsed.length > 0 ? parsed : [{ name: '', phone: '', email: '', notes: '' }]);
      }
    };
    reader.readAsText(file);
  };

  const handleImport = async () => {
    setLoading(true);
    setResult(null);
    try {
      const leadsToImport = manualLeads.filter(l => l.name?.trim());
      if (leadsToImport.length === 0) {
        setResult({ error: 'No valid leads to import' });
        setLoading(false);
        return;
      }
      const { data } = await api.post('/leads/import', {
        leads: leadsToImport,
        source: importMode === 'csv' ? 'csv_import' : adsData.source,
        campaign: adsData.campaign,
        batch_id: `import-${Date.now()}`
      });
      setResult(data.data);
    } catch (err) {
      setResult({ error: err.response?.data?.detail || err.message });
    } finally {
      setLoading(false);
    }
  };

  const addRow = () => setManualLeads([...manualLeads, { name: '', phone: '', email: '', notes: '' }]);
  const removeRow = (idx) => setManualLeads(manualLeads.filter((_, i) => i !== idx));
  const updateRow = (idx, field, value) => {
    const updated = [...manualLeads];
    updated[idx][field] = value;
    setManualLeads(updated);
  };

  const downloadTemplate = () => {
    const csv = 'name,phone,email,notes,ad_set,ad_name\nBudi Santoso,+62812000001,budi@email.com,Interested in Type 45,,\nSiti Rahayu,+62812000002,siti@email.com,From Meta Ads,Ad Set A,Creative 1';
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'lead_import_template.csv';
    a.click();
  };

  return (
    <div className="animate-fade-in" data-testid="lead-import-page">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em' }}>{t('lead_import')}</h1>
        <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>Import leads dari CSV atau platform ads</p>
      </div>

      {/* Import Mode Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button className={`filter-chip ${importMode === 'csv' ? 'active' : ''}`} onClick={() => setImportMode('csv')} data-testid="import-mode-csv">
          <FileText size={14} /> {t('import_from_csv')}
        </button>
        <button className={`filter-chip ${importMode === 'ads' ? 'active' : ''}`} onClick={() => setImportMode('ads')} data-testid="import-mode-ads">
          <Upload size={14} /> {t('import_from_ads')}
        </button>
      </div>

      {/* Import Config */}
      <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
        {importMode === 'csv' && (
          <div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
              <button className="btn-pill btn-pill-secondary" onClick={() => fileRef.current?.click()} data-testid="csv-upload-btn">
                <Upload size={14} style={{ display: 'inline', marginRight: 6 }} />Upload CSV
              </button>
              <button className="btn-pill btn-pill-secondary" onClick={downloadTemplate} data-testid="csv-template-btn">
                <Download size={14} style={{ display: 'inline', marginRight: 6 }} />Download Template
              </button>
              <input ref={fileRef} type="file" accept=".csv" onChange={handleCSVUpload} style={{ display: 'none' }} />
            </div>
            <p style={{ fontSize: 12, color: '#94a3b8', marginBottom: 8 }}>
              Format CSV: name, phone, email, notes, ad_set, ad_name (header di baris pertama)
            </p>
          </div>
        )}

        {importMode === 'ads' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>Platform</label>
              <select value={adsData.source} onChange={e => setAdsData({ ...adsData, source: e.target.value })}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }} data-testid="ads-source-select">
                <option value="meta_ads">Meta Ads (Facebook/Instagram)</option>
                <option value="google_ads">Google Ads</option>
                <option value="tiktok_ads">TikTok Ads</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>{t('campaign')}</label>
              <input value={adsData.campaign} onChange={e => setAdsData({ ...adsData, campaign: e.target.value })}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 14, fontFamily: 'inherit' }}
                placeholder="Campaign name" data-testid="ads-campaign-input" />
            </div>
          </div>
        )}
      </div>

      {/* Leads Table */}
      <div className="glass-card" style={{ overflow: 'hidden', marginBottom: 20 }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontWeight: 700, fontSize: 14 }}>Data Lead ({manualLeads.length})</span>
          <button className="btn-pill btn-pill-secondary" style={{ padding: '6px 14px', fontSize: 12 }} onClick={addRow} data-testid="add-import-row">
            + Tambah Baris
          </button>
        </div>
        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
          <table className="sipro-table" data-testid="import-table">
            <thead>
              <tr>
                <th>#</th>
                <th>{t('name')} *</th>
                <th>{t('phone')}</th>
                <th>{t('email')}</th>
                <th>{t('notes')}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {manualLeads.map((lead, idx) => (
                <tr key={idx}>
                  <td style={{ color: '#94a3b8', fontSize: 12 }}>{idx + 1}</td>
                  {['name', 'phone', 'email', 'notes'].map(field => (
                    <td key={field}>
                      <input value={lead[field] || ''} onChange={e => updateRow(idx, field, e.target.value)}
                        style={{ width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid #e2e8f0', fontSize: 13, fontFamily: 'inherit' }}
                        data-testid={`import-row-${idx}-${field}`} />
                    </td>
                  ))}
                  <td>
                    <button onClick={() => removeRow(idx)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', fontSize: 16 }}>x</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Import Button */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <button className="btn-pill btn-pill-primary" onClick={handleImport} disabled={loading} data-testid="import-submit-btn">
          {loading ? 'Importing...' : t('import_leads')} ({manualLeads.filter(l => l.name?.trim()).length} leads)
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="glass-card animate-fade-in" style={{ padding: 20, marginTop: 16 }} data-testid="import-result">
          {result.error ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#ef4444' }}>
              <AlertCircle size={20} /> <span style={{ fontWeight: 600 }}>{result.error}</span>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, color: '#22c55e' }}>
                <CheckCircle size={20} /> <span style={{ fontWeight: 700 }}>Import Selesai!</span>
              </div>
              <div style={{ display: 'flex', gap: 20 }}>
                <div><span style={{ fontWeight: 700, fontSize: 20, color: '#22c55e' }}>{result.imported}</span><div style={{ fontSize: 11, color: '#94a3b8' }}>Imported</div></div>
                <div><span style={{ fontWeight: 700, fontSize: 20, color: '#f59e0b' }}>{result.duplicates}</span><div style={{ fontSize: 11, color: '#94a3b8' }}>Duplikat</div></div>
                <div><span style={{ fontWeight: 700, fontSize: 20, color: '#ef4444' }}>{result.errors?.length || 0}</span><div style={{ fontSize: 11, color: '#94a3b8' }}>Error</div></div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
