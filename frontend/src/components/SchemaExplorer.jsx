import { Database, Table as TableIcon, ChevronRight, ChevronDown } from 'lucide-react';
import { useWorkspace } from '../hooks/useWorkspace';
import { useState } from 'react';

export default function SchemaExplorer() {
  const { workspace } = useWorkspace();
  const [collapsed, setCollapsed] = useState(false);
  const [expandedTables, setExpandedTables] = useState({});

  if (!workspace?.schema) return null;

  const toggleTable = (tableName) => {
    setExpandedTables(prev => ({ ...prev, [tableName]: !prev[tableName] }));
  };

  return (
    <aside className={`transition-all duration-300 ease-in-out border-r border-white/10 bg-black/20 backdrop-blur-md flex flex-col ${collapsed ? 'w-16' : 'w-64'}`}>
      <div className="p-4 flex items-center justify-between border-b border-white/5">
        {!collapsed && <div className="flex items-center gap-2 font-medium text-gray-200"><Database size={16} /> Schema</div>}
        <button onClick={() => setCollapsed(!collapsed)} className="p-1.5 hover:bg-white/10 rounded text-gray-400 mx-auto">
          <Database size={16} />
        </button>
      </div>
      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
          {Object.entries(workspace.schema).map(([tableName, columns]) => (
            <div key={tableName} className="text-sm">
              <button 
                onClick={() => toggleTable(tableName)}
                className="flex items-center gap-2 w-full text-left py-1.5 px-2 hover:bg-white/5 rounded text-gray-300 transition-colors"
              >
                {expandedTables[tableName] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <TableIcon size={14} className="text-blue-400" />
                <span className="truncate">{tableName}</span>
              </button>
              {expandedTables[tableName] && (
                <div className="pl-8 py-1 space-y-1">
                  {columns.map((col, i) => (
                    <div key={i} className="flex justify-between items-center text-xs text-gray-500 py-0.5">
                      <span className="truncate pr-2">{col.column}</span>
                      <span className="uppercase text-[10px] bg-white/5 px-1 rounded">{col.type}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
