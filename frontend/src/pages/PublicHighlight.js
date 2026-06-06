import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import Logo from '../components/Logo';
import { ArrowLeft, Eye } from '@phosphor-icons/react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function PublicHighlight() {
  const { id } = useParams();
  const [reel, setReel] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios.get(`${API}/highlights/${id}`)
      .then(({ data }) => setReel(data))
      .catch(() => setError('Highlight not found or no longer available.'));
  }, [id]);

  return (
    <div className="min-h-screen">
      <nav className="border-b border-[#262626] bg-[#0A0A0A]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/"><Logo /></Link>
          <Link to="/" className="text-sm font-bold text-[#A3A3A3] hover:text-white flex items-center gap-1" data-testid="back-home">
            <ArrowLeft size={16} weight="bold" /> HOME
          </Link>
        </div>
      </nav>
      <div className="max-w-4xl mx-auto p-6">
        {error && <p className="text-[#A3A3A3]">{error}</p>}
        {!error && !reel && <p className="text-[#A3A3A3]">Loading...</p>}
        {reel && (
          <div data-testid="public-highlight-watch">
            <h1 className="text-2xl md:text-3xl font-black tracking-tighter mb-2" style={{fontFamily:'Chivo'}}>{reel.title}</h1>
            <p className="text-sm text-[#A3A3A3] mb-1">
              by <Link to={`/u/${reel.user_id}`} className="text-white hover:text-[#FF3B30] font-bold">{reel.username}</Link>
              {reel.game_name && <> · {reel.game_name}</>}
            </p>
            <p className="text-xs text-[#A3A3A3] mb-4 flex items-center gap-1">
              <Eye size={12} weight="bold" /> {reel.view_count} views
            </p>
            <video
              src={`${process.env.REACT_APP_BACKEND_URL}${reel.video_url}`}
              className="w-full bg-black"
              controls
              autoPlay
              playsInline
              data-testid="public-highlight-video"
            />
            <p className="text-xs text-[#A3A3A3] mt-4">
              Powered by <Link to="/" className="text-[#FF3B30] font-bold hover:underline">GOMOFOS</Link> — esports staking platform.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default PublicHighlight;
