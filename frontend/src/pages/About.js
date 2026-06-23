import React from 'react';
import StaticPage from '../components/StaticPage';

export default function About() {
  return (
    <StaticPage tag="ABOUT" title="About Us" testId="about-page">
      <p>GoMofos is the staking platform for serious gamers. We let you bet on yourself — head-to-head against another player, or in tournaments with a winner-takes-the-pot stake.</p>
      <p>Built by gamers, for gamers. Nothing is mocked. Every credit you stake is real.</p>
    </StaticPage>
  );
}
