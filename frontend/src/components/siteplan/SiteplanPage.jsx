import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useLang } from '../../contexts/LanguageContext';
import api from '../../lib/api';
import { Map, Eye, X } from 'lucide-react';

function formatCurrency(num) {
  if (!num) return 'Rp 0';
  if (num >= 1e9) return `Rp ${(num / 1e9).toFixed(1)}M`;
  return `Rp ${num.toLocaleString('id-ID')}`;
}

export default function SiteplanPage() {
  const [searchParams] = useSearchParams();
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(searchParams.get('project') || '');
  const [siteplanData, setSiteplanData] = useState(null);
  const [viewMode, setViewMode] = useState('sales');
  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);
  const { t } = useLang();

  useEffect(() => { loadProjects(); }, []);
  useEffect(() => { if (selectedProject) loadSiteplan(); }, [selectedProject, viewMode]);

  const loadProjects = async () => {
    try {
      const { data } = await api.get('/projects');
      setProjects(data.data);
      if (!selectedProject && data.data.length > 0) setSelectedProject(data.data[0].id);
    } catch {}
  };

  const loadSiteplan = async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/siteplan/${selectedProject}`, { params: { view_mode: viewMode } });
      setSiteplanData(data.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const getNodeColor = (node) => {
    const colorMap = siteplanData?.color_map || {};
    if (viewMode === 'sales') return colorMap[node.status] || '#94a3b8';
    if (viewMode === 'construction') return colorMap[node.construction_status] || '#94a3b8';
    if (viewMode === 'finance') return colorMap[node.payment_status] || '#94a3b8';
    return colorMap[node.status] || '#94a3b8';
  };

  const viewModes = [
    { key: 'sales', label: t('sales_view'), color: '#22c55e' },
    { key: 'construction', label: t('construction_view'), color: '#3b82f6' },
    { key: 'finance', label: t('finance_view'), color: '#f59e0b' },
    { key: 'management', label: t('management_view'), color: '#7c3aed' },
  ];

  // Group nodes by block
  const blocks = {};
  (siteplanData?.nodes || []).forEach(node => {
    const block = node.block || 'Other';
    if (!blocks[block]) blocks[block] = [];
    blocks[block].push(node);
  });

  const summary = siteplanData?.summary || {};

  return (
    <div className="animate-fade-in" data-testid="siteplan-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em' }}>
            <Map size={24} style={{ display: 'inline', marginRight: 8, verticalAlign: 'middle' }} />
            Interactive {t('siteplan')}
          </h1>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 2 }}>
            {siteplanData?.project?.name || 'Pilih proyek'}
          </p>
        </div>
        <select value={selectedProject} onChange={e => setSelectedProject(e.target.value)}
          style={{ padding: '10px 16px', borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13, fontFamily: 'inherit', background: 'white' }} data-testid="siteplan-project-select">
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      {/* Mini Dashboard */}
      <div className="mini-dashboard" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
        {[
          { label: t('total'), value: summary.total || 0, bg: '#f8fafc', color: '#1e293b' },
          { label: t('available'), value: summary.available || 0, bg: '#f1f5f9', color: '#64748b' },
          { label: t('reserved'), value: summary.reserved || 0, bg: '#fef3c7', color: '#92400e' },
          { label: t('booked'), value: summary.booked || 0, bg: '#fed7aa', color: '#9a3412' },
          { label: t('sold'), value: summary.sold || 0, bg: '#d1fae5', color: '#065f46' },
        ].map((item, i) => (
          <div key={i} className="mini-dashboard-card" style={{ background: item.bg }}>
            <div className="kpi-number" style={{ color: item.color }}>{item.value}</div>
            <div className="kpi-label">{item.label}</div>
          </div>
        ))}
      </div>

      {/* View Mode Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {viewModes.map(mode => (
          <button
            key={mode.key}
            className={`filter-chip ${viewMode === mode.key ? 'active' : ''}`}
            onClick={() => setViewMode(mode.key)}
            data-testid={`siteplan-mode-${mode.key}`}
            style={viewMode === mode.key ? { background: mode.color, borderColor: mode.color } : {}}
          >
            <Eye size={14} /> {mode.label}
          </button>
        ))}
      </div>

      {/* Siteplan Canvas */}
      <div className="glass-card" style={{ padding: 24, position: 'relative', minHeight: 400 }} ref={containerRef}>
        {loading && <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>{t('loading')}</div>}

        {!loading && Object.keys(blocks).length > 0 && (
          <div>
            {/* Legend */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
              {Object.entries(siteplanData?.color_map || {}).map(([status, color]) => (
                <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 600 }}>
                  <div style={{ width: 14, height: 14, borderRadius: 4, background: color }} />
                  <span style={{ color: '#64748b', textTransform: 'capitalize' }}>{status.replace('_', ' ')}</span>
                </div>
              ))}
            </div>

            {/* Blocks Grid */}
            {Object.entries(blocks).sort().map(([blockName, nodes]) => (
              <div key={blockName} style={{ marginBottom: 24 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: '#475569', marginBottom: 10, letterSpacing: '0.02em' }}>
                  Blok {blockName}
                </h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {nodes.sort((a, b) => parseInt(a.number) - parseInt(b.number)).map(node => (
                    <div
                      key={node.id || node.unit_id}
                      className="siteplan-node"
                      data-testid={`siteplan-node-${node.label}`}
                      style={{
                        position: 'relative',
                        width: 60, height: 42,
                        background: getNodeColor(node),
                        cursor: 'pointer'
                      }}
                      onMouseEnter={(e) => {
                        setHoveredNode(node);
                        const rect = e.currentTarget.getBoundingClientRect();
                        setMousePos({ x: rect.left + rect.width / 2, y: rect.top - 10 });
                      }}
                      onMouseLeave={() => setHoveredNode(null)}
                      onClick={() => setSelectedNode(node)}
                    >
                      {node.label}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && Object.keys(blocks).length === 0 && (
          <div style={{ textAlign: 'center', padding: 60, color: '#94a3b8' }}>
            <Map size={48} style={{ marginBottom: 12 }} />
            <p>Belum ada unit. Generate unit dari halaman proyek terlebih dahulu.</p>
          </div>
        )}

        {/* Hover Tooltip */}
        {hoveredNode && (
          <div className="sipro-tooltip" style={{ position: 'fixed', left: mousePos.x, top: mousePos.y - 50, transform: 'translateX(-50%)' }}>
            <div style={{ fontWeight: 700 }}>{hoveredNode.label}</div>
            <div style={{ fontSize: 11 }}>Status: {hoveredNode.status} | {formatCurrency(hoveredNode.price)}</div>
          </div>
        )}
      </div>

      {/* Selected Unit Detail Panel */}
      {selectedNode && (
        <div className="glass-card animate-slide-in" style={{ marginTop: 16, padding: 24 }} data-testid="siteplan-detail-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 18, fontWeight: 700 }}>Unit {selectedNode.label}</h3>
            <button onClick={() => setSelectedNode(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
              <X size={20} />
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>{t('status')}</div>
              <span className={`status-badge status-${selectedNode.status}`}>{selectedNode.status}</span>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>{t('type')}</div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{selectedNode.unit_type || '-'}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>{t('price')}</div>
              <div style={{ fontSize: 14, fontWeight: 700 }}>{formatCurrency(selectedNode.price)}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>Konstruksi</div>
              <span className={`status-badge status-${selectedNode.construction_status}`}>{selectedNode.construction_status?.replace('_', ' ') || '-'}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
