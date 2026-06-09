import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAgents, fetchDirectives } from '../services/fetchService';
import { createDirective, deleteDirective } from '../services/mutateService';
import { Spinner } from './Icons';
import ReviewOffers from './ReviewOffers';

import { executeCommand } from '../utils/terminalCommands';

const CommandCenter = () => {
  const queryClient = useQueryClient();
  const [inputText, setInputText] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [mentionFilter, setMentionFilter] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  
  // Master terminal log. This stores EVERYTHING in order.
  const [terminalOutput, setTerminalOutput] = useState([
    { id: 'init-1', text: 'Console initialized. All services operational.', type: 'system', isLocal: true },
    { id: 'init-3', text: 'Welcome. Type /help for available commands.', type: 'info', isLocal: true },
  ]);
  
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  const { data: agents = [], isLoading: agentsLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
  });

  const { data: directives = [] } = useQuery({
    queryKey: ['directives'],
    queryFn: fetchDirectives,
    refetchInterval: 5000,
  });

  const createDirectiveMutation = useMutation({
    mutationFn: createDirective,
    onSuccess: (newDir) => {
      queryClient.invalidateQueries({ queryKey: ['directives'] });
      setInputText('');
      // Append the newly created directive to the log immediately
      appendDirective(newDir);
    },
    onError: (error) => {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to issue directive';
      appendOutput(`[ERROR] ${errorMessage}`, 'error');
    }
  });

  const deleteDirectiveMutation = useMutation({
    mutationFn: deleteDirective,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['directives'] });
      appendOutput(`[SYSTEM] Directive #${id} removed successfully.`, 'success');
    },
    onError: (error) => {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to remove directive';
      appendOutput(`[ERROR] ${errorMessage}`, 'error');
    }
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [terminalOutput]);

  const filteredAgents = agents.filter(a => a.name.toLowerCase().includes(mentionFilter));

  // Clamp selected index when the filtered list changes
  useEffect(() => {
    if (selectedIndex >= filteredAgents.length && filteredAgents.length > 0) {
      setSelectedIndex(filteredAgents.length - 1);
    } else if (filteredAgents.length === 0) {
      setSelectedIndex(0);
    }
  }, [filteredAgents.length, selectedIndex]);

  const appendOutput = (text, type = 'info') => {
    setTerminalOutput(prev => [...prev, { id: Date.now() + Math.random(), text, type, isLocal: true }]);
  };

  const appendDirective = (dir) => {
    setTerminalOutput(prev => [...prev, { id: `dir-ref-${Date.now()}-${dir.id}`, dirId: dir.id, dirSnapshot: dir, isDirectiveRef: true }]);
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInputText(value);

    const cursorPosition = e.target.selectionStart;
    const textBeforeCursor = value.slice(0, cursorPosition);
    const mentionMatch = textBeforeCursor.match(/@(\w*)$/);

    if (mentionMatch) {
      setShowSuggestions(true);
      setMentionFilter(mentionMatch[1].toLowerCase());
      setSelectedIndex(0);
    } else {
      setShowSuggestions(false);
    }
  };

  const handleAgentSelect = (agentName) => {
    const cursorPosition = inputRef.current.selectionStart;
    const textBeforeCursor = inputText.slice(0, cursorPosition);
    const textAfterCursor = inputText.slice(cursorPosition);
    const newTextBeforeCursor = textBeforeCursor.replace(/@\w*$/, `@${agentName} `);
    setInputText(newTextBeforeCursor + textAfterCursor);
    setShowSuggestions(false);
    inputRef.current.focus();
  };

  const handleKeyDown = (e) => {
    if (showSuggestions && filteredAgents.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev < filteredAgents.length - 1 ? prev + 1 : prev));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        handleAgentSelect(filteredAgents[selectedIndex].name);
      } else if (e.key === 'Escape') {
        setShowSuggestions(false);
      }
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim() || createDirectiveMutation.isPending) return;

    let content = inputText.trim();
    
    if (content.startsWith('/')) {
        appendOutput(`> ${content}`, 'user');
        executeCommand(content, {
          appendOutput,
          appendDirective,
          setTerminalOutput,
          directives,
          deleteDirectiveMutation
        });
        setInputText('');
        return;
    }

    appendOutput(`> ${content}`, 'user');

    let agentId = null;
    const mentionRegex = /@(\w+)\b/;
    const match = content.match(mentionRegex);

    if (match) {
      const mentionedName = match[1];
      const matchedAgent = agents.find(a => a.name.toLowerCase() === mentionedName.toLowerCase());
      if (matchedAgent) {
        agentId = matchedAgent.id;
      }
    }

    createDirectiveMutation.mutate({
      content,
      agent: agentId,
    });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'text-yellow-400';
      case 'in_progress': return 'text-blue-400';
      case 'completed': return 'text-green-400';
      case 'failed': return 'text-red-400';
      default: return 'text-zinc-400';
    }
  };

  return (
    <div className="flex flex-col gap-0">
      <ReviewOffers />
      <div className="bg-black border border-zinc-800 rounded-lg overflow-hidden flex flex-col font-mono text-sm h-96 shadow-2xl">
        {/* Header */}
        <div className="bg-zinc-900 border-b border-zinc-800 px-4 py-2 flex items-center justify-between">
          <div className="text-zinc-300 font-bold tracking-wider flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            MANAGEMENT CONSOLE
          </div>
          <div className="text-zinc-500 text-xs">
            v2.1.0
          </div>
        </div>

      {/* Directives History */}
      <div 
        ref={scrollRef}
        className="flex-1 p-4 overflow-y-auto bg-black text-zinc-300 space-y-3"
      >
        {agentsLoading ? (
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

      {/* Input Area */}
      <div className="relative border-t border-zinc-800 bg-zinc-950 p-2">
        {showSuggestions && filteredAgents.length > 0 && (
          <div className="absolute bottom-full left-0 w-full mb-1 bg-zinc-900 border border-zinc-700 rounded-md shadow-lg overflow-hidden z-10 max-h-32 overflow-y-auto">
            {filteredAgents.map((agent, index) => (
              <button
                key={agent.id}
                type="button"
                className={`w-full text-left px-3 py-2 text-zinc-300 hover:bg-zinc-800 focus:outline-none ${
                  index === selectedIndex ? 'bg-zinc-800' : ''
                }`}
                onClick={() => handleAgentSelect(agent.name)}
                onMouseEnter={() => setSelectedIndex(index)}
              >
                @{agent.name}
              </button>
            ))}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="flex gap-2">
          <div className="text-green-500 font-bold pl-2 py-2">{'>'}</div>
          <input
            ref={inputRef}
            type="text"
            maxLength={10000}
            value={inputText}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Type a command..."
            className="flex-1 bg-transparent text-zinc-100 placeholder-zinc-700 focus:outline-none py-2"
            disabled={createDirectiveMutation.isPending || deleteDirectiveMutation.isPending}
            autoComplete="off"
          />
          <button 
            type="submit"
            disabled={!inputText.trim() || createDirectiveMutation.isPending || deleteDirectiveMutation.isPending}
            className="px-4 py-2 bg-zinc-800 text-zinc-300 font-bold rounded hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            EXECUTE
          </button>
        </form>
      </div>
    </div>
  </div>
);
};

export default CommandCenter;
