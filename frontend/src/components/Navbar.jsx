import { Settings, Share2, MessageSquare } from 'lucide-react';
import { useState } from 'react';
import ShareModal from './ShareModal';
import SettingsModal from './SettingsModal';
import { useWorkspace } from '../hooks/useWorkspace';

export default function Navbar({ onChatToggle }) {
  const [showShare, setShowShare] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const { role } = useWorkspace();

  return (
    <>
      <nav className="h-16 flex items-center justify-between px-6 bg-white/5 backdrop-blur-md border-b border-white/10 z-10">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-lg">A</div>
          <h1 className="text-xl font-semibold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">Asklytics</h1>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={onChatToggle}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-300 hover:text-white"
            title="Toggle Chat"
          >
            <MessageSquare size={20} />
          </button>
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
