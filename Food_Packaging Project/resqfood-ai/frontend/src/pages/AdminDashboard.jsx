import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import { api } from '../services/api';

export default function AdminDashboard({ user, onLogout }) {
  const [impact, setImpact] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const data = await api.analytics.impact();
      setImpact(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="app-layout">
      <Sidebar user={user} onLogout={onLogout} />
      <div className="main-content">
        <div className="page-header">
          <h1>Admin Command Centre</h1>
          <p>System-wide monitoring and control for ResQFood AI</p>
        </div>

        {error && <div className="error-banner">{error}</div>}
        {loading ? (
          <div className="loading"><div className="spinner" />Loading dashboard...</div>
        ) : impact && (
          <>
            {/* Primary Impact Stats */}
            <div className="section">
              <div className="section-title">🎯 Impact Overview</div>
              <div className="stats-grid">
                <StatCard color="green" icon="🍽" value={impact.total_meals_rescued} label="Meals Rescued" />
                <StatCard color="blue" icon="⚖️" value={`${impact.total_weight_rescued_kg} kg`} label="Food Redistributed" />
                <StatCard color="purple" icon="🚚" value={impact.total_deliveries_completed} label="Deliveries Completed" />
                <StatCard color="cyan" icon="🏢" value={impact.total_recipients_served} label="Recipients Served" />
              </div>
            </div>

            {/* Environmental Estimates */}
            <div className="section">
              <div className="section-title">🌱 Estimated Environmental Impact</div>
              <div className="stats-grid">
                <StatCard color="green" icon="♻️" value={`${impact.estimated_waste_prevented_kg} kg`} label="Estimated Waste Prevented" />
                <StatCard color="blue" icon="🌍" value={`${impact.estimated_co2_saved_kg} kg`} label="Estimated CO₂ Saved" />
                <StatCard color="cyan" icon="💧" value={`${impact.estimated_water_saved_liters} L`} label="Estimated Water Saved" />
                <StatCard color="orange" icon="₹" value={`₹${impact.estimated_cost_saved}`} label="Estimated Value Saved" />
              </div>
              <p className="text-xs text-muted" style={{ marginTop: '-0.5rem' }}>
                * Environmental values are calculated estimates based on standard food waste impact factors
              </p>
            </div>

            {/* System Status */}
            <div className="section">
              <div className="section-title">⚡ System Status</div>
              <div className="stats-grid">
                <StatCard color="orange" icon="📦" value={impact.active_surplus} label="Active Surplus" />
                <StatCard color="purple" icon="📋" value={impact.active_requests} label="Active Requests" />
                <StatCard color="blue" icon="🚗" value={impact.active_deliveries} label="Active Deliveries" />
                <StatCard color="green" icon="🍳" value={impact.registered_kitchens} label="Registered Kitchens" />
                <StatCard color="cyan" icon="🏢" value={impact.registered_ngos} label="Registered NGOs" />
                <StatCard color="red" icon="🚴" value={impact.registered_drivers} label="Registered Drivers" />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function StatCard({ color, icon, value, label }) {
  return (
    <div className={`stat-card ${color}`}>
      <div className="icon">{icon}</div>
      <div className="value">{value}</div>
      <div className="label">{label}</div>
    </div>
  );
}
