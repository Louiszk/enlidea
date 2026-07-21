import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAgents, fetchDirectives } from '../services/fetchService';
import { createDirective, deleteDirective } from '../services/mutateService';
import TerminalWindow from './TerminalWindow';
import ReviewOffers from './ReviewOffers';
import { AgentDirective } from '../api/generated/api';
import { TerminalOutputItem } from '../types';

import { executeCommand } from '../utils/terminalCommands';



const CommandCenter = () => {
  const queryClient = useQueryClient();
  const [inputText, setInputText] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [mentionFilter, setMentionFilter] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  
  // Master terminal log. This stores EVERYTHING in order.
  const [terminalOutput, setTerminalOutput] = useState<TerminalOutputItem[]>([
    { id: 'init-1', text: 'Console initialized. All services operational.', type: 'system', isLocal: true },
    { id: 'init-3', text: 'Welcome. Type /help for available commands.', type: 'info', isLocal: true },
  ]);
  
  const inputRef = useRef<HTMLInputElement>(null);

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
      const errorMessage = (axios.isAxiosError(error) && error.response?.data?.detail) ? error.response.data.detail : error.message || 'Failed to issue directive';
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
      const errorMessage = (axios.isAxiosError(error) && error.response?.data?.detail) ? error.response.data.detail : error.message || 'Failed to remove directive';
      appendOutput(`[ERROR] ${errorMessage}`, 'error');
    }
  });



  const filteredAgents = agents.filter(a => a.name.toLowerCase().includes(mentionFilter));

  // Clamp selected index when the filtered list changes
  useEffect(() => {
    if (selectedIndex >= filteredAgents.length && filteredAgents.length > 0) {
      setSelectedIndex(filteredAgents.length - 1);
    } else if (filteredAgents.length === 0) {
      setSelectedIndex(0);
    }
  }, [filteredAgents.length, selectedIndex]);

  const appendOutput = (text: string, type: string = 'info') => {
    setTerminalOutput(prev => [...prev, { id: Date.now() + Math.random(), text, type, isLocal: true }]);
  };

  const appendDirective = (dir: AgentDirective) => {
    setTerminalOutput(prev => [...prev, { id: `dir-ref-${Date.now()}-${dir.id}`, dirId: dir.id, dirSnapshot: dir, isDirectiveRef: true }]);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInputText(value);

    const cursorPosition = e.target.selectionStart || 0;
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

  const handleAgentSelect = (agentName: string) => {
    const cursorPosition = inputRef.current?.selectionStart || 0;
    const textBeforeCursor = inputText.slice(0, cursorPosition);
    const textAfterCursor = inputText.slice(cursorPosition);
    const newTextBeforeCursor = textBeforeCursor.replace(/@\w*$/, `@${agentName} `);
    setInputText(newTextBeforeCursor + textAfterCursor);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || createDirectiveMutation.isPending) return;

    const content = inputText.trim();
    
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

    let agentId: number | undefined = undefined;
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
        <TerminalWindow
          terminalOutput={terminalOutput}
          directives={directives}
          isLoading={agentsLoading}
        />

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
