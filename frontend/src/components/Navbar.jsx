import { Settings, Share2, MessageSquare, RefreshCw, PlayCircle } from 'lucide-react';
import { useState } from 'react';
import ShareModal from './ShareModal';
import SettingsModal from './SettingsModal';
import { useWorkspace } from '../hooks/useWorkspace';
import logo from "../assets/logo.png"; // adjust path if needed

export default function Navbar({ onChatToggle, onNarrate }) {
  const [showShare, setShowShare] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const { role, refreshDashboard, loading } = useWorkspace();

  return (
    <>
      <nav className="h-16 flex items-center justify-between px-6 bg-white/5 backdrop-blur-md border-b border-white/10 z-10">
<div className="flex items-center gap-3">
  <img
    src={logo}
    alt="Asklytics Logo"
    className="w-30 h-12 object-contain"
  />
  
</div>
        <div className="flex items-center gap-3">
          <button 
            onClick={onChatToggle}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-300 hover:text-white"
            title="Toggle Chat"
          >
            <MessageSquare size={20} />
          </button>

          {(role === 'owner' || role === 'edit') && (
            <button 
              onClick={refreshDashboard}
              disabled={loading}
              className={`p-2 rounded-lg transition-colors text-gray-300 hover:text-white ${loading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-white/10'}`}
              title="Sync Data"
            >
              <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
            </button>
          )}
          {role === 'owner' && (
            <>
              <button 
                onClick={() => setShowShare(true)}
                className="flex items-center gap-2 px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 rounded-lg transition-colors border border-blue-500/30"
              >
                <Share2 size={16} /> Share
              </button>
              <button 
                onClick={() => setShowSettings(true)}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-300 hover:text-white"
                title="Settings"
              >
                <Settings size={20} />
              </button>
            </>
          )}
        </div>
      </nav>
      {showShare && <ShareModal onClose={() => setShowShare(false)} />}
      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </>
  );
}
