import React from 'react';
import StaticPage from '../components/StaticPage';

export default function Terms() {
  return (
    <StaticPage tag="LEGAL" title="Terms of Use" testId="terms-page">
      <p>By using GoMofos you agree to the terms below. We'll publish the full legal copy here as it's finalised.</p>
      <ul className="list-disc pl-5 space-y-1">
        <li>You must be 18 or older to stake credits.</li>
        <li>Disputes are resolved by an admin; their decision is final.</li>
        <li>Cheating, account-sharing, or stake-fixing results in immediate suspension and forfeit of credits.</li>
        <li>Credits are non-refundable once a match is in progress.</li>
      </ul>
    </StaticPage>
  );
}
