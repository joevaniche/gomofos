import React from 'react';

export default function BackgroundVideo() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none" style={{zIndex: -10}}>
      <video
        autoPlay
        loop
        muted
        playsInline
        poster="/gomofos-bg-poster.jpg"
        className="absolute inset-0 w-full h-full object-cover"
        style={{opacity: 0.35}}
      >
        <source
          src="/gomofos-bg.mp4"
          type="video/mp4"
        />
      </video>
      <div
        className="absolute inset-0"
        style={{
          background: 'linear-gradient(180deg, rgba(10,10,10,0.55) 0%, rgba(10,10,10,0.75) 50%, rgba(10,10,10,0.9) 100%)'
        }}
      ></div>
    </div>
  );
}
