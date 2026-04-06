import { Responsive, WidthProvider } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { useWorkspace } from '../hooks/useWorkspace';
import ChartTile from './ChartTile';
import { useMemo, useState } from 'react';
import { useAgent } from '../hooks/useAgent';
import api from '../api/client';

const ResponsiveGridLayout = WidthProvider(Responsive);

export default function Dashboard() {
  const { workspaceId, workspace, updateDashboard, role } = useWorkspace();
  const { isActive, steps, currentStepIndex, targetChartIndex, activateNarrator } = useAgent();
  const [narratingChart, setNarratingChart] = useState(null);
  
  const activeStep = isActive ? steps[currentStepIndex] : null;

  const handleDelete = (index) => {
    if (role === 'view') return;
    updateDashboard(workspace.dashboard.filter((_, i) => i !== index));
  };

  const handleNarrate = async (index) => {
    const existingSteps = workspace.dashboard[index]?._narration_steps;
    if (existingSteps && existingSteps.length > 0) {
      activateNarrator(existingSteps, index);
      return;
    }
    
    if (role === 'view') return;
    
    setNarratingChart(index);
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      const url = token ? `/workspaces/${workspaceId}/charts/${index}/narrate?token=${token}` : `/workspaces/${workspaceId}/charts/${index}/narrate`;
      const res = await api.post(url);
      const steps = res.data.narration_steps;
      
      // Update local state without waiting for DB re-fetch
      workspace.dashboard[index]._narration_steps = steps;
      activateNarrator(steps, index);
    } catch (e) {
      console.error(e);
    } finally {
      setNarratingChart(null);
    }
  };

  const layouts = useMemo(() => {
    const lg = workspace?.dashboard?.map((chart, i) => ({
      i: i.toString(),
      x: chart.grid_layout?.x ?? (i % 2) * 6,
      y: chart.grid_layout?.y ?? Math.floor(i / 2) * 4,
      w: chart.grid_layout?.w ?? 6,
      h: chart.grid_layout?.h ?? 4,
      minW: 3,
      minH: 3
    })) || [];
    return { lg, md: lg, sm: lg };
  }, [workspace?.dashboard]);

  const onLayoutChange = (layout) => {
    if (!workspace?.dashboard || (role !== 'owner' && role !== 'edit')) return;
    
    let changed = false;
    const newDashboard = workspace.dashboard.map((chart, i) => {
      const l = layout.find(item => item.i === i.toString());
      if (l) {
        if (
          chart.grid_layout?.x !== l.x ||
          chart.grid_layout?.y !== l.y ||
          chart.grid_layout?.w !== l.w ||
          chart.grid_layout?.h !== l.h
        ) {
          changed = true;
          return { ...chart, grid_layout: { x: l.x, y: l.y, w: l.w, h: l.h } };
        }
      }
      return chart;
    });

    if (changed) {
      updateDashboard(newDashboard);
    }
  };

  if (!workspace?.dashboard?.length) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 relative">
        <div className="absolute inset-0 bg-transparent pointer-events-none" />
        No charts available. Use the chat to generate some!
      </div>
    );
  }

  return (
    <div className="pb-8 overflow-x-hidden min-h-full">
      <ResponsiveGridLayout
        className="layout"
        layouts={layouts}
        onLayoutChange={onLayoutChange}
        breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
        cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
        rowHeight={100}
        useCSSTransforms={true}
        draggableHandle=".drag-handle"
        isDraggable={role === 'owner' || role === 'edit'}
        isResizable={role === 'owner' || role === 'edit'}
      >
        {workspace.dashboard.map((chart, i) => {
          const isTarget = activeStep?.target_id === `chart_${i}`;
          const hX = activeStep?.type === 'datapoint' && isTarget ? activeStep.x : null;
          const spotlit = isActive && targetChartIndex === i;
          
          return (
            <div key={i.toString()} id={`chart_${i}`}>
              <ChartTile 
                payload={chart} 
                highlightX={hX} 
                isSpotlit={spotlit}
                onDelete={role !== 'view' ? () => handleDelete(i) : undefined}
                onNarrate={role !== 'view' || chart._narration_steps ? () => handleNarrate(i) : undefined}
                isNarrating={narratingChart === i} 
              />
            </div>
          );
        })}
      </ResponsiveGridLayout>
    </div>
  );
}
