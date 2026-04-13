import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { saveNode, savePaper } from '../services/socialService';
import { useAuth } from '../contexts/AuthContext';
import { Spinner, BookmarkIcon } from './Icons';

const SaveButton = ({ targetId, targetType = 'node', queryId, handleError }) => {
  const [isSaved, setIsSaved] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const { user, loading, refreshSaves, refreshPaperSaves } = useAuth();
  const queryClient = useQueryClient();

  const isPaper = targetType === 'paper';
  const queryKeyStr = isPaper ? 'paper' : 'node';
  const savedArrayName = isPaper ? 'saved_papers' : 'saved_nodes';
  const refreshFn = isPaper ? refreshPaperSaves : refreshSaves;
  const cacheId = parseInt(queryId || targetId, 10);

  const saveMutation = useMutation({
    mutationFn: () => isPaper ? savePaper(targetId) : saveNode(targetId),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: [queryKeyStr, cacheId] });
      const previousData = queryClient.getQueryData([queryKeyStr, cacheId]);
      
      queryClient.setQueryData([queryKeyStr, cacheId], old => {
        if (!old) return old;
        const newSaves = (old.saves || 0) + (isSaved ? -1 : 1);
        const newData = {
          ...old,
          saves: newSaves,
          is_saved: !isSaved
        };

        if (!isPaper && old.coordinating_agent) {
          newData.coordinating_agent = {
            ...old.coordinating_agent,
            total_saves: (old.coordinating_agent.total_saves || 0) + (isSaved ? -1 : 1)
          };
        }
        return newData;
      });
  
      return { previousData };
    },
    onError: (error, variables, context) => {
      queryClient.setQueryData([queryKeyStr, cacheId], context.previousData);
    },
    onSuccess: () => {
      refreshFn(targetId);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['userNodes'] });
      queryClient.invalidateQueries({ queryKey: ['userSavedPapers'] });
      queryClient.invalidateQueries({ queryKey: ['papersFeed'] });
      setTimeout(() => setIsAnimating(false), 600);
    }
  });
  

  useEffect(() => {
    if (!loading && user && user[savedArrayName]) {
      const savedStatus = user[savedArrayName].includes(targetId);
      setIsSaved(savedStatus);
    }
  }, [targetId, loading, user, savedArrayName]);

  const handleSave = () => {
    if (user){
      setIsAnimating(true);
      saveMutation.mutate();
    } else {
      handleError();
    }
  };

  if (loading) {
    return <Spinner size="xs" />;
  }

  return (
    <div className='flex justify-end relative'> 
      <button
        onClick={handleSave}
        className="flex items-center px-4 py-2 rounded-full bg-gradient-to-r from-purple-300 to-blue-400 text-white font-semibold transition-all duration-300 hover:from-purple-400 hover:to-blue-600 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-opacity-50 max-w-fit overflow-hidden"
        disabled={isAnimating || saveMutation.isPending}
      >
        <div className="relative mr-2">
          <BookmarkIcon fill={isSaved ? "currentColor" : "none"} />
          {isAnimating && (
            <>
              <div className="absolute inset-0 animate-ripple-1 bg-white rounded-full opacity-0"></div>
              <div className="absolute inset-0 animate-ripple-2 bg-white rounded-full opacity-0"></div>
              <div className="absolute inset-0 animate-ripple-3 bg-white rounded-full opacity-0"></div>
            </>
          )}
        </div>
        {isSaved ? "Saved" : "Save"}
      </button>
    </div> 
  );
};

export default SaveButton;
