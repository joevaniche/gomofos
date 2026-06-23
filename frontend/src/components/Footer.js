import React from 'react';
import { Link } from 'react-router-dom';
import Logo from './Logo';

const TABS = [
  { to: '/about',     label: 'ABOUT US' },
  { to: '/careers',   label: 'CAREERS' },
  { to: '/support',   label: 'SUPPORT' },
  { to: '/contact',   label: 'CONTACT' },
  { to: '/terms',     label: 'TERMS OF USE' },
  { to: '/privacy',   label: 'PRIVACY POLICY' },
];

export default function Footer() {
  return (
    <footer
      data-testid="site-footer"
      className="
        relative z-10 mt-16 border-t border-[#262626] bg-[#0A0A0A]/95 backdrop-blur-sm
        px-6 py-10
      "
    >
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-8">
        <div className="flex flex-col items-start gap-3">
          <Logo size="small" />
          <p className="text-[10px] tracking-[0.25em] text-[#525252] uppercase">
            © {new Date().getFullYear()} GoMofos · Stake · Compete · Dominate
          </p>
        </div>
        <nav className="flex flex-wrap gap-x-6 gap-y-3" data-testid="footer-nav">
          {TABS.map(t => (
            <Link
              key={t.to}
              to={t.to}
              data-testid={`footer-${t.to.slice(1)}`}
              className="text-xs font-bold tracking-[0.2em] text-[#A3A3A3] hover:text-[#FF3B30] transition-colors"
            >
              {t.label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
