import Plot from 'react-plotly.js';
import { GripHorizontal } from 'lucide-react';
import { useMemo, useState, useEffect } from 'react';

export default function ChartTile({ payload }) {
    const [layout, setLayout] = useState(payload.layout);
    
    useEffect(() => {
      setLayout({
          ...payload.layout,
          autosize: true,
          margin: { t: 40, r: 20, l: 40, b: 40 },
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { color: '#e2e8f0' }
      });
    }, [payload.layout]);

  return (
    <div className="w-full h-full bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden flex flex-col shadow-xl group hover:border-white/20 transition-colors">
      <div className="h-8 flex items-center justify-between px-3 bg-white/5 border-b border-white/5">
        <span className="text-xs font-medium text-gray-300 truncate max-w-[80%]">{payload.layout?.title?.text || payload.layout?.title || 'Chart'}</span>
        <div className="drag-handle cursor-move p-1 text-gray-500 hover:text-white transition-colors opacity-0 group-hover:opacity-100">
          <GripHorizontal size={14} />
        </div>
      </div>
      <div className="flex-1 w-full relative">
        <Plot
          data={payload.data}
          layout={layout}
          useResizeHandler={true}
          style={{ width: '100%', height: '100%' }}
          config={{ displayModeBar: false, responsive: true }}
        />
      </div>
    </div>
  );
}
