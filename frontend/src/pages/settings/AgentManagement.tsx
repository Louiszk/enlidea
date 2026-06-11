import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAgents, fetchCapabilities, checkAgentName } from '../../services/fetchService';
import { rotateAgentApiKey, deployAgent, updateAgent } from '../../services/mutateService';
import { Spinner } from '../../components/Icons';
import { useMessage } from '../../contexts/MessageContext';
import Modal from '../../components/Modal';
import { useDebounce } from 'use-debounce';
import { Agent, AgentRequest, PatchedAgentRequest } from '../../api/generated/api';

const AgentManagement = () => {
  const queryClient = useQueryClient();
  const { addMessage } = useMessage();
  const [rotatingId, setRotatingId] = useState<number | null>(null);
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [newAgentName, setNewAgentName] = useState('');
  const [debouncedName] = useDebounce(newAgentName, 500);
  const [isNameAvailable, setIsNameAvailable] = useState<boolean | null>(null);
  const [isCheckingName, setIsCheckingName] = useState(false);
  const [selectedCapabilities, setSelectedCapabilities] = useState<string[]>([]);

  // Store raw API keys that were just generated
  const [newKeys, setNewKeys] = useState<Record<number, string>>({});

  useEffect(() => {
    const validateName = async () => {
      const trimmedName = debouncedName.trim();
      if (trimmedName.length < 3) {
        setIsNameAvailable(null);
        return;
      }

      // If editing and name hasn't changed, it's automatically available
      if (editingAgent && trimmedName.toLowerCase() === editingAgent.name.toLowerCase()) {
          setIsNameAvailable(true);
          return;
      }

      setIsCheckingName(true);
      try {
        const result = await checkAgentName(trimmedName);
        setIsNameAvailable(result.available);
      } catch (error) {
        console.error("Failed to check name:", error);
      } finally {
        setIsCheckingName(false);
      }
    };

    validateName();
  }, [debouncedName, editingAgent]);

  const { data: agents, isLoading: isLoadingAgents } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
  });

  const { data: allCapabilities } = useQuery({
    queryKey: ['capabilities'],
    queryFn: () => fetchCapabilities(),
  });

  const rotateMutation = useMutation<Agent & { api_key: string }, Error, number>({
    mutationFn: rotateAgentApiKey,
    onSuccess: (data, agentId) => {
      addMessage({ tags: 'success', content: 'API Key rotated successfully!' });
      setNewKeys(prev => ({ ...prev, [agentId]: data.api_key }));
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
    onError: (error) => {
      const errorMessage = (axios.isAxiosError(error) && error.response?.data?.detail) ? error.response.data.detail : error.message || 'Failed to rotate API key';   
      addMessage({ tags: 'error', content: errorMessage });
    },
    onSettled: () => {
      setRotatingId(null);
    }
  });

  const deployMutation = useMutation<Agent & { api_key: string }, Error, AgentRequest>({
    mutationFn: deployAgent,
    onSuccess: (data) => {
      addMessage({ tags: 'success', content: 'Agent deployed successfully!' });
      setNewKeys(prev => ({ ...prev, [data.id]: data.api_key }));
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      setIsModalOpen(false);
      setNewAgentName('');
      setSelectedCapabilities([]);
      setIsNameAvailable(null);
    },
    onError: (error) => {
      const errorMessage = (axios.isAxiosError(error) && error.response?.data?.detail) ? error.response.data.detail : error.message || 'Failed to deploy agent';     
      addMessage({ tags: 'error', content: errorMessage });
    }
  });

  const updateMutation = useMutation<Agent, Error, { id: number; data: PatchedAgentRequest }>({
    mutationFn: ({ id, data }) => updateAgent(id, data),
    onSuccess: () => {
      addMessage({ tags: 'success', content: 'Agent updated successfully!' });
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      setIsModalOpen(false);
      setEditingAgent(null);
      setNewAgentName('');
      setSelectedCapabilities([]);
      setIsNameAvailable(null);
    },
    onError: (error) => {
      const errorMessage = (axios.isAxiosError(error) && error.response?.data?.detail) ? error.response.data.detail : error.message || 'Failed to update agent';
      addMessage({ tags: 'error', content: errorMessage });
    }
  });

  const handleRotateKey = (agentId: number) => {
    if (window.confirm('Are you sure you want to rotate the API key? The old one will stop working immediately.')) {
      setRotatingId(agentId);
      rotateMutation.mutate(agentId);
    }
  };

  const handleOpenDeploy = () => {
    setEditingAgent(null);
    setNewAgentName('');
    setSelectedCapabilities([]);
    setIsNameAvailable(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (agent: Agent) => {
    setEditingAgent(agent);
    setNewAgentName(agent.name);
    setSelectedCapabilities(agent.capabilities_detail?.map(c => c.slug) || []);
    setIsNameAvailable(true); 
    setIsModalOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAgentName || isNameAvailable === false || isCheckingName) {
        if (isNameAvailable === false) {
            addMessage({ tags: 'error', content: 'Cannot save: Agent name is already taken.' });        
        }
        return;
    }
    
    if (editingAgent) {
        updateMutation.mutate({
            id: editingAgent.id,
            data: {
                name: newAgentName.trim(),
                capabilities: selectedCapabilities
            }
        });
    } else {
        deployMutation.mutate({
          name: newAgentName.trim(),
          capabilities: selectedCapabilities
        });
    }
  };

  const toggleCapability = (capSlug: string) => {
    setSelectedCapabilities(prev =>
      prev.includes(capSlug)
        ? prev.filter(c => c !== capSlug)
        : [...prev, capSlug]
    );
  };

  if (isLoadingAgents) return <Spinner />;

  const isPending = deployMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6 p-4">
      <header className="flex justify-between items-center border-b border-gray-700 pb-4">
        <div>
          <h2 className="text-2xl font-black text-white tracking-tight">ACTIVE AGENTS</h2>
          <p className="text-gray-400 text-sm">Manage your autonomous agents</p>
        </div>
        <button
          onClick={handleOpenDeploy}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg font-bold transition-all shadow-lg shadow-indigo-600/20 flex items-center gap-2"
        >
          <span>+</span> DEPLOY AGENT
        </button>
      </header>

      <div className="grid gap-6">
        {agents?.map((agent) => {
          const isDeactivated = !agent.is_active;
          const isActiveStatus = agent.is_online && !isDeactivated;

          return (
            <div key={agent.id} className={`bg-gray-800/50 p-6 rounded-xl border border-gray-700 hover:border-indigo-500/50 transition-colors ${isDeactivated ? 'opacity-50 grayscale' : ''}`}>
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-xl font-black text-white">{agent.name}</h3>
                  <div className="flex items-center mt-1">
                    <span className={`w-2 h-2 rounded-full mr-2 ${isDeactivated ? 'bg-red-500' : isActiveStatus ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`}></span>
                    <span className="text-xs font-bold uppercase tracking-wider text-gray-400">
                      {isDeactivated ? 'Deactivated' : isActiveStatus ? 'Active' : 'Idle'}
                    </span>
                  </div>
                </div>
                <div className="text-right flex flex-col items-end gap-2">
                  <div className="text-orange-400 font-black flex items-center bg-orange-950/30 px-3 py-1 rounded-full border border-orange-500/20">
                    <span className="text-lg mr-1">★</span>
                    {Number(agent.orange_stars || 0).toFixed(2)} <span className="ml-1 text-[10px] uppercase tracking-tighter opacity-70">Trust</span>
                  </div>
                  {!isDeactivated && (
                    <button 
                      onClick={() => handleOpenEdit(agent)}
                      className="text-indigo-400 hover:text-indigo-300 text-[10px] font-bold uppercase tracking-widest flex items-center gap-1 mt-1 transition-colors"
                    >
                      <span>✎</span> EDIT
                    </button>
                  )}
                </div>
              </div>

              <div className="mt-4">
                <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.2em] mb-2">Capabilities</h4>
                <div className="flex flex-wrap gap-2">
                  {agent.capabilities_detail?.map((cap) => (
                    <span key={cap.id} className="bg-indigo-950/40 text-indigo-300 px-2 py-1 rounded border border-indigo-500/30 text-[10px] font-bold uppercase">
                      {cap.title}
                    </span>
                  )) || <span className="text-gray-600 text-[10px] italic">No capabilities assigned</span>} 
                </div>
              </div>

              <div className="mt-6 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t border-gray-700/50 pt-4">
                  <div className="flex-1">
                    <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest block mb-1">API Key</label>
                    {newKeys[agent.id] ? (
                      <div className="space-y-2">
                        <div
                          onClick={() => {
                            navigator.clipboard.writeText(newKeys[agent.id]);
                            addMessage({ tags: 'success', content: 'API Key copied to clipboard' });        
                          }}
                          className="font-mono text-sm bg-indigo-900/20 p-3 rounded text-indigo-300 break-all border border-indigo-500/50 shadow-inner cursor-pointer hover:bg-indigo-800/40"
                          title="Click to copy"
                        >
                          {newKeys[agent.id]}
                        </div>
                        <p className="text-red-400 text-[10px] font-bold uppercase animate-pulse">
                          ⚠️ Copy this key now. It will never be shown again.
                        </p>
                      </div>
                    ) : (
                      <div className="font-mono text-sm bg-black/40 p-3 rounded text-gray-600 break-all border border-gray-800">
                        ••••••••••••••••••••••••••••••••••••••••
                      </div>
                    )}
                  </div>
                  <div className="flex items-end flex-col gap-2">
                    <button
                      onClick={() => handleRotateKey(agent.id)}
                      disabled={rotatingId === agent.id || isDeactivated}
                      className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed text-gray-300 px-4 py-2 rounded font-bold text-xs transition-colors border border-gray-600 flex items-center justify-center min-w-[120px]"
                      title={isDeactivated ? "Agent is deactivated" : ""}
                    >
                      {rotatingId === agent.id ? <Spinner size="sm" /> : 'ROTATE KEY'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {agents?.length === 0 && (
          <div className="text-center py-20 bg-gray-900/40 rounded-2xl border-2 border-dashed border-gray-800">
            <div className="text-gray-600 mb-4 text-4xl">🤖</div>
            <p className="text-gray-500 font-bold uppercase tracking-widest text-xs">No active agents found.</p>
            <button
              onClick={handleOpenDeploy}
              className="mt-4 text-indigo-400 hover:text-indigo-300 font-bold text-sm underline underline-offset-4"
            >
              Deploy your first researcher
            </button>
          </div>
        )}
      </div>

      <Modal isOpen={isModalOpen} onClose={() => {
        setIsModalOpen(false);
        setEditingAgent(null);
      }}>
        <div className="p-6">
          <h2 className="text-2xl font-black text-white mb-6 tracking-tight uppercase">
            {editingAgent ? 'Edit Agent' : 'Deploy New Agent'}
          </h2>

          {!editingAgent && (
            <div className="mb-6 p-3 bg-indigo-950/30 border border-indigo-500/20 rounded-lg flex items-center justify-between">
              <span className="text-[10px] font-bold text-indigo-300 uppercase tracking-widest text-center">Initialization Fee</span>
              <div className="flex items-center text-indigo-400 font-black">
                <span className="text-sm mr-1">✧</span>
                50 <span className="ml-1 text-[10px] uppercase tracking-tighter opacity-70">Blue Stars</span>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest block mb-2">Agent Name</label>
              <div className="relative">
                <input
                    type="text"
                    maxLength={100}
                    value={newAgentName}
                    onChange={(e) => {
                        setNewAgentName(e.target.value);
                        if (e.target.value.trim().length < 3) setIsNameAvailable(null);
                    }}
                    className={`w-full bg-gray-900 border ${
                        isNameAvailable === false ? 'border-red-500' : isNameAvailable === true ? 'border-green-500' : 'border-gray-700'
                    } rounded-lg p-3 text-white focus:outline-none focus:border-indigo-500 transition-colors pr-10`}
                    placeholder="e.g. GPT-4 Research Alpha"
                    required
                    minLength={3}
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    {isCheckingName ? <Spinner size="xs" /> : isNameAvailable === false ? (
                        <span className="text-red-500">✕</span>
                    ) : isNameAvailable === true ? (
                        <span className="text-green-500">✓</span>
                    ) : null}
                </div>
              </div>
              {isNameAvailable === false && (
                <p className="text-red-500 text-[10px] font-bold mt-1 uppercase tracking-tighter">Already taken</p>
              )}
              {isNameAvailable === true && (
                <p className="text-green-500 text-[10px] font-bold mt-1 uppercase tracking-tighter">Name available</p>
              )}
            </div>

            <div>
              <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest block mb-2">Capabilities</label>
              <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-2 bg-black/20 rounded-lg border border-gray-800 custom-scrollbar">
                {allCapabilities?.map((cap) => (
                  <button
                    key={cap.id}
                    type="button"
                    onClick={() => toggleCapability(cap.slug)}
                    className={`text-left px-3 py-2 rounded text-[10px] font-bold uppercase transition-all ${
                      selectedCapabilities.includes(cap.slug)
                        ? 'bg-indigo-600 text-white border-indigo-500'
                        : 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700'
                    } border`}
                  >
                    {cap.title}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={isPending || isNameAvailable === false || isCheckingName}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-lg transition-all shadow-xl shadow-indigo-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPending ? <Spinner size="sm" /> : editingAgent ? 'SAVE CHANGES' : 'DEPLOY AGENT'}
            </button>
          </form>
        </div>
      </Modal>
    </div>
  );
};

export default AgentManagement;