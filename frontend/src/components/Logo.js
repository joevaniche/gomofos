import React from 'react';
import { Link } from 'react-router-dom';

export default function Logo({ size = 'default' }) {
  const heights = {
    small: 'h-8',
    default: 'h-12',
    large: 'h-20',
  };
  return (
    <Link to="/" data-testid="site-logo" className="flex items-center hover:opacity-80 transition-opacity">
      <img
        src="/gomofos-logo.png"
        alt="GoMofos"
        className={`${heights[size]} w-auto object-contain drop-shadow-[0_0_8px_rgba(0,0,0,0.6)]`}
      />
    </Link>
  );
}
