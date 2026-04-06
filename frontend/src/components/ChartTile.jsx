import Plot from 'react-plotly.js';
import { GripHorizontal } from 'lucide-react';
import { useMemo, useState, useEffect } from 'react';

export default function ChartTile({ payload, highlightX, isSpotlit }) {
    const [layout, setLayout] = useState(payload.layout);
    
    useEffect(() => {
      const { width, height, ...restLayout } = payload.layout || {};
      const isPie = payload.data?.some(d => d.type === 'pie');
      
      let shouldShowLegend = true;
      if (isPie) {
          const sliceCount = payload.data[0]?.labels?.length || payload.data[0]?.values?.length || 0;
          shouldShowLegend = sliceCount > 1;
      } else {
          shouldShowLegend = payload.data?.length > 1;
      }

      // Remove the title from the plot itself since it's already in the header
      const { title, ...layoutWithoutTitle } = restLayout;

      setLayout({
          ...layoutWithoutTitle,
          autosize: true,
          margin: isPie ? { t: 20, r: 10, l: 10, b: 40 } : { t: 20, r: 20, l: 40, b: 40 },
          showlegend: shouldShowLegend,
          legend: isPie ? { orientation: 'h', yanchor: 'top', y: -0.1, xanchor: 'center', x: 0.5, ...layoutWithoutTitle.legend } : layoutWithoutTitle.legend,
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { color: '#e2e8f0' }
      });
    }, [payload.layout, payload.data]);

    const highlightedData = useMemo(() => {
        if (!payload.data || highlightX == null) return payload.data;
        
        return payload.data.map(trace => {
            if (trace.type === 'pie' || !trace.x) return trace;
            
            const newMarker = { ...(trace.marker || {}) };
            const colors = [];
            const opacities = [];
            
            for (let i = 0; i < trace.x.length; i++) {
                // loose equality to mix strings/numbers like "2023" == 2023
                // eslint-disable-next-line eqeqeq
                if (trace.x[i] == highlightX) {
                    colors.push('#6366f1');
                    opacities.push(1.0);
                } else {
                    colors.push('#94a3b8');
                    opacities.push(0.25);
                }
            }
            
            newMarker.color = colors;
            newMarker.opacity = opacities;
            
            return {
                ...trace,
                marker: newMarker
            };
        });
    }, [payload.data, highlightX]);

  return (
    <div className="w-full h-full min-w-[200px] min-h-[200px] bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden flex flex-col shadow-xl group hover:border-white/20 transition-colors resize">
      <div className="h-8 flex shrink-0 items-center justify-between px-3 bg-white/5 border-b border-white/5">
        <span className="text-xs font-medium text-gray-300 truncate max-w-[80%]">{payload.layout?.title?.text || payload.layout?.title || 'Chart'}</span>
        <div className="drag-handle cursor-move p-1 text-gray-500 hover:text-white transition-colors opacity-0 group-hover:opacity-100">
          <GripHorizontal size={14} />
        </div>
      </div>
      <div className="flex-1 w-full relative overflow-hidden min-h-0 min-w-0">
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}>
          <Plot
            data={highlightedData}
            layout={layout}
            useResizeHandler={true}
            style={{ width: '100%', height: '100%' }}
            config={{ displayModeBar: false, responsive: true }}
          />
        </div>
      </div>
    </div>
  );
}
