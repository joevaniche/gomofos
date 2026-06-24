import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Logo from './Logo';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, ShieldStar, CaretDown } from '@phosphor-icons/react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';

// Single source of truth for the top nav so every page shows the same tabs.
//
// IMPORTANT layout note:
// ProtectedRoute wraps page content in `xl:pr-[200px]` so the AdRail has room on
// the right. TopNav escapes that padding via `xl:-mr-[200px]` so the nav bar
// spans the FULL screen and visually sits OVER the ad column (z-50).
export default function TopNav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const handleLogout = async () => { await logout(); navigate('/login'); };

  const isAdmin = user?.role === 'admin';
  const canManageAds = user?.can_manage_ads === true;

  const items = [
    { to: '/dashboard',     label: 'DASHBOARD',     testid: 'nav-dashboard' },
    { to: '/tournaments',   label: 'TOURNAMENTS',   testid: 'nav-tournaments' },
    { to: '/competitions',  label: 'COMPETITIONS',  testid: 'nav-competitions' },
    { to: '/prizes',        label: 'PRIZES',        testid: 'nav-prizes' },
    { to: '/players',       label: 'PLAYERS',       testid: 'nav-players' },
    { to: '/games',         label: 'GAMES',         testid: 'nav-games' },
    { to: '/leaderboard',   label: 'LEADERBOARD',   testid: 'nav-leaderboard' },
    { to: '/profile',       label: 'PROFILE',       testid: 'nav-profile' },
  ];

  // Admin tools — condensed into a single ADMIN dropdown.
  const adminItems = [
    ...(isAdmin ? [
      { to: '/admin/disputes', label: 'Disputes',     testid: 'nav-admin-disputes' },
      { to: '/admin/latency',  label: 'Latency',      testid: 'nav-admin-latency' },
    ] : []),
    ...(isAdmin || canManageAds ? [
      { to: '/admin/ads',           label: 'Ads',         testid: 'nav-admin-ads' },
      { to: '/admin/ads/analytics', label: 'Ad analytics', testid: 'nav-admin-analytics' },
    ] : []),
    ...(isAdmin ? [
      { to: '/admin/ad-managers', label: 'Ad managers', testid: 'nav-admin-ad-managers' },
    ] : []),
  ];

  const isActive = (to) => pathname === to || (to !== '/dashboard' && pathname.startsWith(to));
  const adminActive = pathname.startsWith('/admin');

  return (
    <nav
      data-testid="top-nav"
      className="
        relative z-50 border-b border-[#262626] bg-[#0A0A0A]/95 backdrop-blur-md
        xl:-mr-[200px]
      "
    >
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between flex-wrap gap-y-2">
        <Logo />
        <div className="flex items-center gap-5 flex-wrap">
          {items.map(it => (
            <Link key={it.to} to={it.to} data-testid={it.testid}
              className={`text-sm font-bold transition-colors ${
                isActive(it.to) ? 'text-[#FF3B30]' : 'text-[#A3A3A3] hover:text-white'
              }`}>
              {it.label}
            </Link>
          ))}

          {adminItems.length > 0 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  data-testid="nav-admin-dropdown"
                  className={`text-sm font-bold flex items-center gap-1 transition-colors focus:outline-none ${
                    adminActive ? 'text-[#FF3B30]' : 'text-[#F59E0B] hover:text-white'
                  }`}
                >
                  <ShieldStar size={16} weight="fill" />
                  ADMIN
                  <CaretDown size={12} weight="bold" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="end"
                className="bg-[#0A0A0A] border border-[#262626] text-white min-w-[200px]"
                data-testid="admin-dropdown-content"
              >
                <DropdownMenuLabel className="text-[10px] tracking-[0.25em] text-[#525252]">ADMIN TOOLS</DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-[#262626]" />
                {adminItems.map(it => (
                  <DropdownMenuItem
                    key={it.to}
                    onSelect={() => navigate(it.to)}
                    data-testid={it.testid}
                    className={`cursor-pointer text-sm font-bold tracking-wide focus:bg-[#FF3B30]/10 focus:text-[#FF3B30] ${
                      pathname.startsWith(it.to) ? 'text-[#FF3B30]' : 'text-[#A3A3A3]'
                    }`}
                  >
                    {it.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}

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
