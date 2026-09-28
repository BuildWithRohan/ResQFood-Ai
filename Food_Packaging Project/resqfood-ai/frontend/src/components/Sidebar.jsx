import { useNavigate, useLocation } from 'react-router-dom';

const NAV_ITEMS = {
  admin: [
    { path: '/admin', label: 'Dashboard', icon: '📊' },
  ],
  kitchen: [
    { path: '/kitchen', label: 'Dashboard', icon: '🍳' },
  ],
  ngo: [
    { path: '/ngo', label: 'Dashboard', icon: '🏢' },
  ],
  driver: [
    { path: '/driver', label: 'Dashboard', icon: '🚗' },
  ],
};

export default function Sidebar({ user, onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();
  const items = NAV_ITEMS[user.role] || [];
  const initials = user.full_name?.split(' ').map(n => n[0]).join('').toUpperCase() || '?';

  return (
    <div className="sidebar">
      <div className="sidebar-brand">
        <h1>ResQFood AI</h1>
        <p>Predict · Prevent · Allocate · Rescue</p>
      </div>
      <nav className="sidebar-nav">
        {items.map((item) => (
          <a key={item.path}
             className={location.pathname === item.path ? 'active' : ''}
             onClick={() => navigate(item.path)}
             style={{ cursor: 'pointer' }}>
            <span>{item.icon}</span>
            {item.label}
          </a>
        ))}
      </nav>
      <div className="sidebar-user">
        <div className="avatar">{initials}</div>
        <div className="info">
          <div className="name">{user.full_name}</div>
          <div className="role">{user.role}</div>
        </div>
        <button className="btn btn-outline btn-sm" onClick={onLogout}
                style={{ marginLeft: 'auto', padding: '0.3rem 0.6rem', fontSize: '0.65rem' }}>
          Logout
        </button>
      </div>
    </div>
  );
}
