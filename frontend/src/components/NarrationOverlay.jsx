import { useEffect, useState, useRef } from 'react';
import { Play, Pause, SkipForward, SkipBack, X } from 'lucide-react';

export default function NarrationOverlay({ steps, isPlaying, onClose }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [spotlight, setSpotlight] = useState({ x: -1000, y: -1000 });
  const [chartRect, setChartRect] = useState(null);
  
  const utteranceRef = useRef(null);
  const timeoutRef = useRef(null);

  // Initialize synth voices if needed
  
  useEffect(() => {
    window.speechSynthesis.getVoices();
  }, []);

  useEffect(() => {
    if (!isPlaying) {
      window.speechSynthesis.cancel();
      setCurrentIndex(0);
      setPaused(false);
      return;
    }

    if (paused) {
      window.speechSynthesis.pause();
      return;
    } else {
      window.speechSynthesis.resume();
    }

    const step = steps[currentIndex];
    if (!step) {
      onClose(); // Auto close at end
      return;
    }

    const targetElement = document.getElementById(step.target_id);
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      // Allow scroll to settle, then update spotlight
      setTimeout(() => {
        const rect = targetElement.getBoundingClientRect();
        setSpotlight({
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height / 2
        });
        setChartRect({
            top: rect.top, bottom: rect.bottom, 
            left: rect.left, right: rect.right, 
            width: rect.width, height: rect.height
        });
      }, 400); 
    }

    // Prepare speech
    if (utteranceRef.current) {
        utteranceRef.current.onend = null;
        utteranceRef.current.onerror = null;
    }
    window.speechSynthesis.cancel(); 
    const utterance = new SpeechSynthesisUtterance(step.text);
    utteranceRef.current = utterance;
    
    utterance.onend = () => {
      // Small pause between clauses
      timeoutRef.current = setTimeout(() => {
          if (!paused) {
            setCurrentIndex(prev => prev + 1);
          }
      }, 500);
    };

    // If step has duration but speech fails to fire
    let backupTimeout = null;
    if (step.duration) {
       backupTimeout = setTimeout(() => {
         if (window.speechSynthesis.speaking) return; // Speech is working
         if (!paused) setCurrentIndex(prev => prev + 1);
       }, step.duration);
    }

    window.speechSynthesis.speak(utterance);

    return () => {
       if (timeoutRef.current) clearTimeout(timeoutRef.current);
       if (backupTimeout) clearTimeout(backupTimeout);
       if (utteranceRef.current) utteranceRef.current.onend = null;
    }
  }, [currentIndex, isPlaying, paused, steps, onClose]);

  // Handle window resize dynamically
  useEffect(() => {
      const handleResize = () => {
         const step = steps[currentIndex];
         if(!step) return;
         const targetElement = document.getElementById(step.target_id);
         if(targetElement) {
             const rect = targetElement.getBoundingClientRect();
             setSpotlight({
                 x: rect.left + rect.width / 2,
                 y: rect.top + rect.height / 2
             });
             setChartRect({
                 top: rect.top, bottom: rect.bottom, 
                 left: rect.left, right: rect.right, 
                 width: rect.width, height: rect.height
             });
         }
      };
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
  }, [currentIndex, steps]);

  if (!isPlaying) return null;

  const currentStep = steps[currentIndex];
  
  let finalX = spotlight.x - 160;
  let finalY = spotlight.y + 150;

  if (chartRect) {
     const boxW = 320;
     const boxH = 150;

     // 1. Right side
     if (chartRect.right + boxW + 40 < window.innerWidth) {
         finalX = chartRect.right + 20;
         finalY = chartRect.top + chartRect.height / 2 - boxH / 2;
     }
     // 2. Left side
     else if (chartRect.left - boxW - 40 > 0) {
         finalX = chartRect.left - boxW - 20;
         finalY = chartRect.top + chartRect.height / 2 - boxH / 2;
     }
     // 3. Bottom side
     else if (chartRect.bottom + boxH + 40 < window.innerHeight) {
         finalX = chartRect.left + chartRect.width / 2 - boxW / 2;
         finalY = chartRect.bottom + 20;
     }
     // 4. Top side
     else if (chartRect.top - boxH - 40 > 0) {
         finalX = chartRect.left + chartRect.width / 2 - boxW / 2;
         finalY = chartRect.top - boxH - 20;
     } 
     // Fallback if chart covers entire screen
     else {
         finalX = window.innerWidth / 2 - boxW / 2;
         finalY = window.innerHeight - boxH - 40;
     }

     finalX = Math.max(20, Math.min(finalX, window.innerWidth - boxW - 20));
     finalY = Math.max(20, Math.min(finalY, window.innerHeight - boxH - 20));
  }

  return (
    <div className="fixed inset-0 z-[9999] pointer-events-auto transition-all duration-500 ease-in-out">
      {/* 
        We use a div with box-shadow inset or mask-image.
        mask-image is best for making a "spotlight hole" 
      */}
      <div 
         className="absolute inset-0 bg-black/70 transition-all duration-700 ease-in-out"
         style={{
           maskImage: `radial-gradient(circle at ${spotlight.x}px ${spotlight.y}px, transparent 150px, black 250px)`,
           WebkitMaskImage: `radial-gradient(circle at ${spotlight.x}px ${spotlight.y}px, transparent 150px, black 250px)`
         }}
      />

      <div className="absolute top-6 right-6 flex items-center gap-2 bg-slate-900/80 border border-white/20 backdrop-blur-md p-2 rounded-2xl shadow-2xl z-50">
        <button 
          onClick={() => setPaused(!paused)} 
          className="p-3 hover:bg-white/10 rounded-xl text-white transition-colors"
          title={paused ? "Play" : "Pause"}
        >
          {paused ? <Play size={20}/> : <Pause size={20}/>}
        </button>
        <button 
          onClick={() => { 
              if (utteranceRef.current) utteranceRef.current.onend = null;
              window.speechSynthesis.cancel(); 
              setCurrentIndex(c => Math.max(0, c - 1)); 
          }} 
          className="p-3 hover:bg-white/10 rounded-xl text-white transition-colors"
          title="Previous"
        >
          <SkipBack size={20}/>
        </button>
        <button 
          onClick={() => { 
              if (utteranceRef.current) utteranceRef.current.onend = null;
              window.speechSynthesis.cancel(); 
              setCurrentIndex(c => c + 1); 
          }} 
          className="p-3 hover:bg-white/10 rounded-xl text-white transition-colors"
          title="Skip"
        >
          <SkipForward size={20}/>
        </button>
        <button 
          onClick={() => {
              if (utteranceRef.current) utteranceRef.current.onend = null;
              window.speechSynthesis.cancel();
              onClose();
          }} 
          className="p-3 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-xl transition-colors"
          title="Close"
        >
          <X size={20}/>
        </button>
      </div>
      
      {currentStep && (
          <div 
             className="absolute bg-slate-900 border border-indigo-500/50 text-white p-6 rounded-2xl shadow-2xl w-[320px] transition-all duration-700 ease-in-out"
             style={{ 
                left: `${finalX}px`,
                top: `${finalY}px`
             }}
          >
             {currentStep.type === 'datapoint' && currentStep.x && (
               <p className="text-xs text-indigo-400 font-mono mb-2">📍 {currentStep.x}</p>
             )}
             <p className="text-lg font-medium leading-relaxed">{currentStep.text}</p>
             <div className="mt-4 flex gap-1 justify-center">
                {steps.map((_, i) => (
                    <div key={i} className={`w-2 h-2 rounded-full ${i === currentIndex ? 'bg-indigo-500' : 'bg-white/20'}`} />
                ))}
             </div>
          </div>
      )}
    </div>
  );
}
