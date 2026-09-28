import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import Sidebar from '../components/Sidebar';
import { api } from '../services/api';

export default function KitchenDashboard({ user, onLogout }) {
  const [predictions, setPredictions] = useState([]);
  const [history, setHistory] = useState([]);
  const [surplus, setSurplus] = useState([]);
  const [kitchens, setKitchens] = useState([]);
  const [kitchenId, setKitchenId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('prediction');
  const [predicting, setPredicting] = useState(false);
  const [error, setError] = useState('');

  // Surplus form
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    food_name: '', food_category: 'rice_dish', quantity: '', unit: 'meals',
    estimated_weight_kg: '', usable_hours: '3', storage_condition: 'room_temperature',
    location: '', description: '',
  });
  const [imageFile, setImageFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { loadKitchens(); }, []);
  useEffect(() => { if (kitchenId) loadData(); }, [kitchenId]);

  const loadKitchens = async () => {
    try {
      const k = await api.users.kitchens();
      setKitchens(k);
      if (k.length > 0) setKitchenId(k[0].id);
    } catch (e) { setError(e.message); setLoading(false); }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [pred, hist, sur] = await Promise.all([
        api.demand.predictions(kitchenId),
        api.demand.history(kitchenId),
        api.surplus.list({ kitchen_id: kitchenId }),
      ]);
      setPredictions(pred);
      setHistory(hist);
      setSurplus(sur);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const runPrediction = async () => {
    setPredicting(true);
    setError('');
    try {
      await api.demand.predict(kitchenId);
      await loadData();
    } catch (e) { setError(e.message); }
    finally { setPredicting(false); }
  };

  const submitSurplus = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const now = new Date();
      const usableUntil = new Date(now.getTime() + parseFloat(form.usable_hours) * 3600000);
      const data = {
        food_name: form.food_name,
        food_category: form.food_category,
        quantity: parseInt(form.quantity),
        unit: form.unit,
        estimated_weight_kg: parseFloat(form.estimated_weight_kg) || null,
        prepared_at: now.toISOString(),
        usable_until: usableUntil.toISOString(),
        storage_condition: form.storage_condition,
        location: form.location,
        description: form.description,
      };
      const result = await api.surplus.create(data);
      if (imageFile) {
        await api.surplus.uploadImage(result.id, imageFile);
      }
      setShowForm(false);
      setForm({
        food_name: '', food_category: 'rice_dish', quantity: '', unit: 'meals',
        estimated_weight_kg: '', usable_hours: '3', storage_condition: 'room_temperature',
        location: '', description: '',
      });
      setImageFile(null);
      await loadData();
    } catch (e) { setError(e.message); }
    finally { setSubmitting(false); }
  };

  const latestPred = predictions[0];
  const chartData = history.slice(-30).map(h => ({
    date: h.date,
    consumed: h.meals_consumed,
    prepared: h.meals_prepared,
    wasted: h.meals_wasted,
  }));

  return (
    <div className="app-layout">
      <Sidebar user={user} onLogout={onLogout} />
      <div className="main-content">
        <div className="page-header">
          <h1>Kitchen Dashboard</h1>
          <p>{kitchens.find(k => k.id === kitchenId)?.name || 'Kitchen'} — Production & Surplus Management</p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {/* Tab Navigation */}
        <div className="flex gap-1 mb-2">
          {['prediction', 'surplus', 'register'].map(t => (
            <button key={t} className={`btn ${tab === t ? 'btn-primary' : 'btn-outline'} btn-sm`}
                    onClick={() => { setTab(t); if (t === 'register') setShowForm(true); }}>
              {t === 'prediction' ? '📈 Demand Prediction' : t === 'surplus' ? '📦 My Surplus' : '➕ Register Surplus'}
            </button>
          ))}
        </div>

        {loading ? <div className="loading"><div className="spinner" />Loading...</div> : (
          <>
            {/* ── Prediction Tab ─────────────────────────────── */}
            {tab === 'prediction' && (
              <>
                {/* Prediction Summary Cards */}
                {latestPred && (
                  <div className="section">
                    <div className="section-title">🧠 ML Demand Prediction</div>
                    <div className="stats-grid">
                      <div className="stat-card blue">
                        <div className="icon">📊</div>
                        <div className="value">{Math.round(latestPred.historical_average)}</div>
                        <div className="label">Historical Average (meals/day)</div>
                      </div>
                      <div className="stat-card purple">
                        <div className="icon">🤖</div>
                        <div className="value">{latestPred.predicted_demand}</div>
                        <div className="label">Predicted Demand</div>
                      </div>
                      <div className="stat-card green">
                        <div className="icon">✅</div>
                        <div className="value">{latestPred.recommended_production}</div>
                        <div className="label">Recommended Production</div>
                      </div>
                      <div className="stat-card orange">
                        <div className="icon">🔻</div>
                        <div className="value">
                          {Math.max(0, Math.round(latestPred.historical_average) - latestPred.recommended_production)}
                        </div>
                        <div className="label">Surplus Avoided</div>
                      </div>
                    </div>

                    {/* Prediction Details */}
                    <div className="card" style={{ marginBottom: '1.5rem' }}>
                      <div className="card-header">
                        <h2>Prediction Details</h2>
                        <span className="badge cyan">{latestPred.model_type}</span>
                      </div>
                      <div className="grid-2">
                        <div>
                          <p className="text-sm text-muted">Prediction Date</p>
                          <p className="fw-bold">{latestPred.prediction_date}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted">Safety Buffer</p>
                          <p className="fw-bold">+{latestPred.safety_buffer} meals</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted">Confidence Range</p>
                          <p className="fw-bold">{latestPred.confidence_lower} – {latestPred.confidence_upper} meals</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted">Model Error (MAE)</p>
                          <p className="fw-bold">±{latestPred.mae} meals</p>
                        </div>
                      </div>

                      {/* WHY? Explanation */}
                      <div className="reasoning" style={{ marginTop: '1rem' }}>
                        <h4>💡 Why This Prediction?</h4>
                        <p>
                          The {latestPred.model_type} model analysed {history.length} days of historical consumption data.
                          It detected that average daily consumption is ~{Math.round(latestPred.historical_average)} meals,
                          but predicted <strong>{latestPred.predicted_demand}</strong> meals for {latestPred.prediction_date} based
                          on day-of-week patterns, recent trends (rolling averages), and previous-day demand.
                          Adding a safety buffer of {latestPred.safety_buffer} meals gives a recommended production of{' '}
                          <strong>{latestPred.recommended_production}</strong> meals.
                          This could prevent ~{Math.max(0, Math.round(latestPred.historical_average) - latestPred.recommended_production)} meals
                          of unnecessary overproduction.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Historical Chart */}
                <div className="card" style={{ marginBottom: '1.5rem' }}>
                  <div className="card-header">
                    <h2>Historical Consumption (Last 30 Days)</h2>
                  </div>
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }}
                               tickFormatter={(d) => d.slice(5)} />
                        <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                        <Tooltip contentStyle={{ background: '#1a2236', border: '1px solid rgba(148,163,184,0.12)', borderRadius: 8 }} />
                        <Bar dataKey="consumed" fill="#3b82f6" name="Consumed" radius={[2,2,0,0]} />
                        <Bar dataKey="wasted" fill="#ef4444" name="Wasted" radius={[2,2,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : <div className="empty-state"><p>No history data</p></div>}
                </div>

                <button className="btn btn-primary" onClick={runPrediction} disabled={predicting}>
                  {predicting ? '🔄 Running ML Model...' : '🧠 Run New Prediction'}
                </button>
              </>
            )}

            {/* ── Surplus Tab ────────────────────────────────── */}
            {tab === 'surplus' && (
              <div className="section">
                <div className="section-title">📦 Registered Surplus Food</div>
                {surplus.length === 0 ? (
                  <div className="empty-state">
                    <div className="icon">📦</div>
                    <p>No surplus registered yet</p>
                  </div>
                ) : (
                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr>
                          <th>Food</th><th>Qty</th><th>Weight</th><th>Status</th>
                          <th>Remaining Time</th><th>Allocated</th><th>Created</th>
                        </tr>
                      </thead>
                      <tbody>
                        {surplus.map(s => (
                          <tr key={s.id}>
                            <td style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{s.food_name}</td>
                            <td>{s.quantity} {s.unit}</td>
                            <td>{s.estimated_weight_kg ? `${s.estimated_weight_kg} kg` : '–'}</td>
                            <td><StatusBadge status={s.status} /></td>
                            <td><Countdown minutes={s.remaining_minutes} /></td>
                            <td>{s.allocated_quantity}/{s.quantity}</td>
                            <td className="text-muted text-xs">{new Date(s.created_at).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* ── Register Surplus Form ──────────────────────── */}
            {tab === 'register' && (
              <div className="card" style={{ maxWidth: 600 }}>
                <div className="card-header">
                  <h2>Register Surplus Food</h2>
                </div>
                <form onSubmit={submitSurplus}>
                  <div className="form-group">
                    <label>Food Name *</label>
                    <input value={form.food_name} onChange={e => setForm({...form, food_name: e.target.value})}
                           placeholder="e.g. Vegetable Biryani" required />
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Quantity *</label>
                      <input type="number" value={form.quantity} onChange={e => setForm({...form, quantity: e.target.value})}
                             placeholder="40" required min="1" />
                    </div>
                    <div className="form-group">
                      <label>Unit</label>
                      <select value={form.unit} onChange={e => setForm({...form, unit: e.target.value})}>
                        <option value="meals">Meals</option>
                        <option value="kg">Kilograms</option>
                        <option value="servings">Servings</option>
                      </select>
                    </div>
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Estimated Weight (kg)</label>
                      <input type="number" step="0.1" value={form.estimated_weight_kg}
                             onChange={e => setForm({...form, estimated_weight_kg: e.target.value})}
                             placeholder="12" />
                    </div>
                    <div className="form-group">
                      <label>Usable Window (hours) *</label>
                      <input type="number" step="0.5" value={form.usable_hours}
                             onChange={e => setForm({...form, usable_hours: e.target.value})}
                             placeholder="3" required min="0.5" />
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Food Category</label>
                    <select value={form.food_category} onChange={e => setForm({...form, food_category: e.target.value})}>
                      <option value="rice_dish">Rice Dish</option>
                      <option value="bread">Bread/Roti</option>
                      <option value="curry">Curry/Gravy</option>
                      <option value="snack">Snacks</option>
                      <option value="dessert">Dessert</option>
                      <option value="mixed">Mixed/Thali</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Storage Condition</label>
                    <select value={form.storage_condition} onChange={e => setForm({...form, storage_condition: e.target.value})}>
                      <option value="room_temperature">Room Temperature</option>
                      <option value="refrigerated">Refrigerated</option>
                      <option value="hot_holding">Hot Holding</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Food Image</label>
                    <input type="file" accept="image/*" onChange={e => setImageFile(e.target.files[0])}
                           style={{ padding: '0.5rem' }} />
                  </div>
                  <div className="form-group">
                    <label>Description</label>
                    <textarea value={form.description} onChange={e => setForm({...form, description: e.target.value})}
                              placeholder="Optional notes about the food" rows={2} />
                  </div>
                  <button className="btn btn-success" type="submit" disabled={submitting}>
                    {submitting ? 'Registering...' : '✅ Register Surplus'}
                  </button>
                </form>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    eligible: 'green', urgent: 'orange', review_required: 'purple',
    expired: 'red', rejected: 'red', allocated: 'blue',
  };
  return <span className={`badge ${map[status] || 'gray'}`}>{status?.replace(/_/g, ' ')}</span>;
}

function Countdown({ minutes }) {
  if (minutes === null || minutes === undefined) return <span className="text-muted">—</span>;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  const cls = minutes < 30 ? 'urgent' : minutes < 60 ? 'warning' : 'ok';
  return <span className={`countdown ${cls}`}>{h}h {m}m</span>;
}
