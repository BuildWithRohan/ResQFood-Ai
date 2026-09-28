import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { api } from '../services/api';

export default function AllocationPage({ user, onLogout }) {
  const { surplusId } = useParams();
  const navigate = useNavigate();
  const [allocation, setAllocation] = useState(null);
  const [surplus, setSurplus] = useState(null);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { loadData(); }, [surplusId]);

  const loadData = async () => {
    try {
      const s = await api.surplus.get(surplusId);
      setSurplus(s);
      const r = await api.requests.list({ surplus_id: surplusId });
      setRequests(r);
      try {
        const a = await api.allocation.get(surplusId);
        if (a.allocations?.length > 0) setAllocation(a);
      } catch { /* No allocation yet */ }
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const runAllocation = async () => {
    setRunning(true);
    setError('');
    try {
      const result = await api.allocation.run(parseInt(surplusId));
      setAllocation(result);
      await loadData();
    } catch (e) { setError(e.message); }
    finally { setRunning(false); }
  };

  const createDelivery = async () => {
    setCreating(true);
    setError('');
    try {
      await api.deliveries.create({ surplus_id: parseInt(surplusId) });
      alert('Delivery created! Check the Driver dashboard.');
    } catch (e) { setError(e.message); }
    finally { setCreating(false); }
  };

  if (loading) return (
    <div className="app-layout">
      <Sidebar user={user} onLogout={onLogout} />
      <div className="main-content"><div className="loading"><div className="spinner" />Loading...</div></div>
    </div>
  );

  const totalRequested = requests.reduce((s, r) => s + r.requested_quantity, 0);

  return (
    <div className="app-layout">
      <Sidebar user={user} onLogout={onLogout} />
      <div className="main-content">
        <div className="page-header">
          <div className="flex-between">
            <div>
              <h1>🧠 Smart Allocation Engine</h1>
              <p>Intelligent food distribution optimization</p>
            </div>
            <button className="btn btn-outline btn-sm" onClick={() => navigate(-1)}>← Back</button>
          </div>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {/* Food Info */}
        {surplus && (
          <div className="card mb-2">
            <div className="flex-between">
              <div>
                <h2 style={{ fontSize: '1.1rem' }}>{surplus.food_name}</h2>
                <p className="text-sm text-muted">
                  {surplus.kitchen_name} · {surplus.storage_condition?.replace(/_/g, ' ')}
                </p>
              </div>
              <StatusBadge status={surplus.status} />
            </div>
            <div className="stats-grid" style={{ marginTop: '1rem', marginBottom: 0 }}>
              <MiniStat label="Available" value={`${surplus.quantity} ${surplus.unit}`} color="green" />
              <MiniStat label="Weight" value={surplus.estimated_weight_kg ? `${surplus.estimated_weight_kg} kg` : '–'} color="blue" />
              <MiniStat label="Remaining Time" value={formatTime(surplus.remaining_minutes)} color={surplus.remaining_minutes < 60 ? 'red' : 'orange'} />
              <MiniStat label="Total Requested" value={`${totalRequested} meals`} color={totalRequested > surplus.quantity ? 'red' : 'green'} />
            </div>
          </div>
        )}

        {/* Requests Table */}
        <div className="section">
          <div className="section-title">📋 Competing Requests</div>
          {requests.length === 0 ? (
            <div className="empty-state"><p>No requests for this surplus</p></div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Recipient</th><th>Requested</th><th>Urgency</th>
                    <th>Distance</th><th>Status</th><th>Allocated</th>
                  </tr>
                </thead>
                <tbody>
                  {requests.map(r => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{r.ngo_name}</td>
                      <td>{r.requested_quantity} meals</td>
                      <td><UrgencyBadge urgency={r.urgency} /></td>
                      <td>{r.ngo_distance_km ? `${r.ngo_distance_km} km` : '–'}</td>
                      <td><StatusBadge status={r.status} /></td>
                      <td style={{ fontWeight: 700, color: r.allocated_quantity > 0 ? 'var(--accent-green)' : 'var(--text-muted)' }}>
                        {r.allocated_quantity}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Demand vs Supply warning */}
          {totalRequested > (surplus?.quantity || 0) && (
            <div style={{
              marginTop: '1rem', padding: '0.75rem 1rem', background: 'var(--accent-red-dim)',
              border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-sm)',
            }}>
              <strong style={{ color: 'var(--accent-red)' }}>⚠️ Supply Shortage:</strong>
              <span className="text-sm" style={{ marginLeft: '0.5rem' }}>
                {totalRequested} meals requested but only {surplus?.quantity} available
                → {totalRequested - (surplus?.quantity || 0)} meals cannot be fulfilled
              </span>
            </div>
          )}
        </div>

        {/* Run Allocation Button */}
        {!allocation && requests.length > 0 && (
          <button className="btn btn-primary btn-lg" onClick={runAllocation} disabled={running}
                  style={{ marginBottom: '2rem' }}>
            {running ? '🔄 Running Optimization Engine...' : '🧠 Run Smart Allocation Engine'}
          </button>
        )}

        {/* ── Allocation Results ─────────────────────────── */}
        {allocation && (
          <>
            {/* Summary */}
            <div className="section">
              <div className="section-title">📊 Allocation Results</div>
              <div className="alloc-summary">
                <div className="item">
                  <div className="num" style={{ color: 'var(--accent-blue)' }}>{allocation.total_available}</div>
                  <div className="lbl">AVAILABLE</div>
                </div>
                <div className="item">
                  <div className="num" style={{ color: 'var(--accent-orange)' }}>{allocation.total_requested}</div>
                  <div className="lbl">REQUESTED</div>
                </div>
                <div className="item">
                  <div className="num" style={{ color: 'var(--accent-green)' }}>{allocation.total_allocated}</div>
                  <div className="lbl">ALLOCATED</div>
                </div>
                <div className="item">
                  <div className="num" style={{ color: 'var(--accent-red)' }}>{allocation.unfulfilled}</div>
                  <div className="lbl">UNFULFILLED</div>
                </div>
              </div>
            </div>

            {/* Per-NGO Allocation Cards with Explanations */}
            <div className="section">
              <div className="section-title">🎯 Allocation Breakdown</div>
              {allocation.allocations?.map((alloc, idx) => {
                const pct = alloc.requested_quantity > 0
                  ? Math.round((alloc.allocated_quantity / alloc.requested_quantity) * 100) : 0;
                const barColor = pct >= 100 ? 'green' : pct >= 50 ? 'orange' : 'red';

                return (
                  <div key={idx} className="alloc-card">
                    <div className="header">
                      <div>
                        <h3>{alloc.ngo_name}</h3>
                        <span className="text-xs text-muted">
                          Priority Score: {alloc.priority_score?.toFixed(2)}
                        </span>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-green)' }}>
                          {alloc.allocated_quantity}
                        </div>
                        <span className="text-xs text-muted">of {alloc.requested_quantity} requested</span>
                      </div>
                    </div>

                    {/* Fulfillment bar */}
                    <div className="bar-container">
                      <div className={`bar ${barColor}`} style={{ width: `${Math.min(pct, 100)}%` }} />
                    </div>
                    <div className="flex-between text-xs text-muted">
                      <span>{pct}% fulfilled</span>
                      <span><UrgencyBadge urgency={alloc.urgency} /> · {alloc.distance_km} km</span>
                    </div>

                    {/* Factor chips */}
                    {alloc.factors?.length > 0 && (
                      <div className="factors">
                        {alloc.factors.map((f, fi) => (
                          <span key={fi} className={`factor ${f.impact}`}>
                            {f.impact === 'positive' ? '✓' : f.impact === 'negative' ? '✗' : '·'} {f.factor_label}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* WHY? Reasoning */}
                    {alloc.allocation_reasoning && (
                      <div className="reasoning">
                        <h4>💡 Why This Allocation?</h4>
                        <p>{alloc.allocation_reasoning}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Create Delivery Button */}
            <button className="btn btn-success btn-lg" onClick={createDelivery} disabled={creating}>
              {creating ? '🔄 Creating...' : '🚚 Create Delivery & Assign Route'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function MiniStat({ label, value, color }) {
  return (
    <div className={`stat-card ${color}`} style={{ padding: '0.75rem' }}>
      <div className="value" style={{ fontSize: '1.1rem' }}>{value}</div>
      <div className="label">{label}</div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    eligible: 'green', urgent: 'orange', allocated: 'blue', expired: 'red',
    pending: 'orange', fulfilled: 'green', partially_fulfilled: 'cyan', rejected: 'red',
  };
  return <span className={`badge ${map[status] || 'gray'}`}>{status?.replace(/_/g, ' ')}</span>;
}

function UrgencyBadge({ urgency }) {
  const map = { low: 'gray', medium: 'blue', high: 'orange', very_high: 'red', critical: 'red' };
  return <span className={`badge ${map[urgency] || 'gray'}`}>{urgency?.replace(/_/g, ' ')}</span>;
}

function formatTime(minutes) {
  if (!minutes && minutes !== 0) return '—';
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return `${h}h ${m}m`;
}
