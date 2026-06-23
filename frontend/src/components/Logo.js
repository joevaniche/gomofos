import React from 'react';
import { Link } from 'react-router-dom';

// NOTE on caching: we use a NEW filename (gomofos-crest.png) AND a version query
// string. Browser + CDN cache the URL string, so changing either invalidates the
// cache. Bump the `?v=` whenever the crest is updated to force a refetch.
const LOGO_SRC = '/gomofos-crest.png?v=3';

export default function Logo({ size = 'default' }) {
  const heights = {
    small: 'h-8',
    default: 'h-12',
    large: 'h-20',
    xlarge: 'h-40',
  };
  return (
    <Link to="/" data-testid="site-logo" className="flex items-center hover:opacity-80 transition-opacity">
      <img
        src={LOGO_SRC}
        alt="GoMofos"
        className={`${heights[size]} w-auto object-contain drop-shadow-[0_0_8px_rgba(0,0,0,0.6)]`}
      />
    </Link>
  );
}
