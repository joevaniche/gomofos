import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Logo from './Logo';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins } from '@phosphor-icons/react';

// Single source of truth for the top nav so every page shows the same tabs.
export default function TopNav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const handleLogout = async () => { await logout(); navigate('/login'); };

  const items = [
    { to: '/dashboard',     label: 'DASHBOARD',     testid: 'nav-dashboard' },
    { to: '/tournaments',   label: 'TOURNAMENTS',   testid: 'nav-tournaments' },
    { to: '/competitions',  label: 'COMPETITIONS',  testid: 'nav-competitions' },
    { to: '/prizes',        label: 'PRIZES',        testid: 'nav-prizes' },
    { to: '/players',       label: 'PLAYERS',       testid: 'nav-players' },
    { to: '/games',         label: 'GAMES',         testid: 'nav-games' },
    { to: '/leaderboard',   label: 'LEADERBOARD',   testid: 'nav-leaderboard' },
    ...(user?.role === 'admin' ? [{ to: '/admin/disputes', label: 'DISPUTES', testid: 'nav-admin-disputes', accent: true }] : []),
    { to: '/profile',       label: 'PROFILE',       testid: 'nav-profile' },
  ];

  const isActive = (to) => pathname === to || (to !== '/dashboard' && pathname.startsWith(to));

  return (
    <nav className="border-b border-[#262626] bg-[#0A0A0A]/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between flex-wrap gap-y-2">
        <Logo />
        <div className="flex items-center gap-5 flex-wrap">
          {items.map(it => (
            <Link key={it.to} to={it.to} data-testid={it.testid}
              className={`text-sm font-bold transition-colors ${
                isActive(it.to)
                  ? 'text-[#FF3B30]'
                  : it.accent
                    ? 'text-[#F59E0B] hover:text-white'
                    : 'text-[#A3A3A3] hover:text-white'
              }`}>
              {it.label}
            </Link>
          ))}
          <Link to="/wallet" data-testid="nav-wallet"
            className={`text-sm font-bold flex items-center gap-2 ${pathname === '/wallet' ? 'text-[#FF3B30]' : 'text-[#A3A3A3] hover:text-white'}`}>
            <Coins size={18} weight="bold" />{user?.wallet_balance?.toFixed(0) || '0'} CR
          </Link>
          <button onClick={handleLogout} data-testid="nav-logout"
            className="text-sm font-bold text-[#A3A3A3] hover:text-white flex items-center gap-2">
            <SignOut size={18} weight="bold" />LOGOUT
          </button>
        </div>
      </div>
    </nav>
  );
}
