import React from 'react';
import StaticPage from '../components/StaticPage';

export default function Support() {
  return (
    <StaticPage tag="HELP" title="Support" testId="support-page">
      <p>Got a problem with a match, a payout, or a dispute? You're in the right place.</p>
      <ul className="list-disc pl-5 space-y-1">
        <li>Match disputes are reviewed within 24 hours by an admin.</li>
        <li>Wallet top-ups process instantly via Stripe — if you don't see your balance, log out and back in.</li>
        <li>For anything urgent, message <a href="/contact" className="text-[#FF3B30] hover:underline">CONTACT</a>.</li>
      </ul>
    </StaticPage>
  );
}
