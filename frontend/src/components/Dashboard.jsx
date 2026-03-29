import { Responsive, WidthProvider } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { useWorkspace } from '../hooks/useWorkspace';
import ChartTile from './ChartTile';
import { useMemo } from 'react';

const ResponsiveGridLayout = WidthProvider(Responsive);

export default function Dashboard() {
  const { workspace } = useWorkspace();

  const layouts = useMemo(() => {
    const lg = workspace?.dashboard?.map((chart, i) => ({
      i: i.toString(),
      x: (i % 2) * 6,
      y: Math.floor(i / 2) * 4,
      w: 6,
      h: 4,
      minW: 3,
      minH: 3
    })) || [];
    return { lg, md: lg, sm: lg };
  }, [workspace?.dashboard]);

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
        breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
        cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
        rowHeight={100}
        useCSSTransforms={true}
        draggableHandle=".drag-handle"
        isDraggable={true}
        isResizable={true}
      >
        {workspace.dashboard.map((chart, i) => (
          <div key={i.toString()}>
            <ChartTile payload={chart} />
          </div>
        ))}
      </ResponsiveGridLayout>
    </div>
  );
}
