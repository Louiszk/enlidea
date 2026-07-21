import React, { useRef, useEffect } from 'react';
import { Spinner } from './Icons';
import { AgentDirective } from '../api/generated/api';
import { TerminalOutputItem } from '../types';

interface TerminalWindowProps {
  terminalOutput: TerminalOutputItem[];
  directives: AgentDirective[];
  isLoading: boolean;
}

const TerminalWindow: React.FC<TerminalWindowProps> = ({
  terminalOutput,
  directives,
  isLoading,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [terminalOutput]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'text-yellow-400';
      case 'in_progress': return 'text-blue-400';
      case 'completed': return 'text-green-400';
      case 'failed': return 'text-red-400';
      default: return 'text-zinc-400';
    }
  };

  return (
    <div 
      ref={scrollRef}
      className="flex-1 p-4 overflow-y-auto bg-black text-zinc-300 space-y-3"
    >
      {isLoading ? (
        <div className="flex justify-center items-center h-full">
          <Spinner />
        </div>
      ) : (
        <>
          {terminalOutput.map((item) => {
            if (item.isLocal) {
              return (
                <div key={item.id} className={`font-mono ${
                    item.type === 'error' ? 'text-red-400' : 
                    item.type === 'success' ? 'text-green-400' : 
                    item.type === 'system' ? 'text-indigo-400 font-bold' : 
                    item.type === 'user' ? 'text-zinc-500' : 'text-zinc-400'
                }`}>
                    {item.text}
                </div>
              );
            }
            
            if (item.isDirectiveRef) {
              // Find latest data from query, fallback to snapshot
              const liveDir = directives.find(d => d.id === item.dirId);
              const dir = liveDir || item.dirSnapshot;
              if (!dir) return null;

              return (
                <div key={item.id} className="flex flex-col border-l-2 border-zinc-800 pl-3 py-1 mt-2">
                  <div className="flex items-center gap-2 text-xs mb-1">
                    <span className="text-zinc-500">
                      #{dir.id} • {new Date(dir.created_at).toLocaleTimeString()}
                    </span>
                    <span className="text-indigo-400 font-bold">
                      {dir.agent_detail ? `@${dir.agent_detail.name}` : '@broadcast'}
                    </span>
                    <span className={`uppercase font-bold ${getStatusColor(dir.status)}`}>
                      [{dir.status}]
                    </span>
                  </div>
                  <div className="text-zinc-200 break-words mb-1">
                    {dir.content}
                  </div>
                  {dir.agent_response && (
                    <div className="mt-1 text-xs font-mono text-green-400 break-words whitespace-pre-wrap bg-zinc-900/50 p-2 rounded border border-zinc-800/50">
                      <span className="text-zinc-500 mr-2">{`>> [${dir.agent_detail ? dir.agent_detail.name : 'System'}] Output:`}</span>
                      {dir.agent_response}
                    </div>
                  )}
                </div>
              );
            }
            return null;
          })}
        </>
      )}
    </div>
  );
};

export default TerminalWindow;
