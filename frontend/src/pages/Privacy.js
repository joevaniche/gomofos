import React from 'react';
import StaticPage from '../components/StaticPage';

export default function Privacy() {
  return (
    <StaticPage tag="LEGAL" title="Privacy Policy" testId="privacy-page">
      <p>We collect the minimum data needed to run matches, settle stakes, and keep accounts secure.</p>
      <ul className="list-disc pl-5 space-y-1">
        <li><strong>What we store:</strong> email, username, hashed password, wallet balance, match results, latency samples (30-day retention), and any content you upload (avatars, highlight reels, dispute evidence).</li>
        <li><strong>What we don't store:</strong> raw payment card details (handled by Stripe), WhatsApp message bodies (sent via Twilio, not retained).</li>
        <li><strong>Cookies:</strong> HttpOnly session + refresh cookies for auth. No third-party analytics today.</li>
        <li><strong>Deletion:</strong> request account deletion via <a href="/contact" className="text-[#FF3B30] hover:underline">CONTACT</a>; we wipe within 30 days.</li>
      </ul>
    </StaticPage>
  );
}
