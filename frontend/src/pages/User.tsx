import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchUserProfile } from '../services/fetchService';
import UserNodes from '../components/UserNodes';
import { useMessage } from '../contexts/MessageContext';
import Messages from '../components/AlertMessage';
import { useAuth } from '../contexts/AuthContext';
import { followUser, unfollowUser, submitReport } from '../services/socialService';
import NotFound from './NotFound';
import { FulfillmentIcon, FollowerIcon, SavedIcon, VisitsIcon, Spinner, StarIcon } from '../components/Icons';
import ViewFullRating from '../components/ViewFullRating';
import Modal from '../components/Modal';
import { ReportButton, ReportForm } from '../components/Report';
import { getMediaUrl } from '../services/apiClient';
import { Account as ApiUser, ActiveAgent, TargetTypeEnum } from '../api/generated/api';
import { UserProfile } from '../types';

const User = () => {
  const { userId } = useParams();
  const { message, addMessage, removeMessage } = useMessage();
  const { user: authUser, loading: authLoading, refreshFollows } = useAuth();
  const [reportModal, setReportModal] = useState(false);
  const queryClient = useQueryClient();

  const { data: user, isLoading, error } = useQuery<UserProfile>({
    queryKey: ['profile', parseInt(userId!, 10)],
    queryFn: () => fetchUserProfile(userId!),
    staleTime: 60 * 1000 * 2,
    gcTime: 60 * 1000 * 60 * 2,
  });

  const followMutation = useMutation<unknown, Error, boolean>({
    mutationFn: (isFollowing: boolean) => isFollowing ? unfollowUser(userId!) : followUser(userId!),
    onSuccess: (_, isFollowing) => {
      queryClient.setQueryData<UserProfile>(['profile', parseInt(userId!, 10)], (oldData) => {
        if (!oldData) return undefined;
        return {
          ...oldData,
          follower_count: oldData.follower_count + (isFollowing ? -1 : 1),
        };
      });
      refreshFollows(parseInt(userId!, 10), !isFollowing);
    },
    onError: () => {
      addMessage({ tags: 'error', content: "Something went wrong, please try again later or contact our support." });
    },
  });

  const reportMutation = useMutation({
    mutationFn: submitReport,
    onSuccess: () => {
      addMessage({ tags: 'success', content: "Successfully submitted the report. Thank you!" });
      setReportModal(false);
    },
    onError: () => {
      addMessage({ tags: 'error', content: "Failed to submit report. Please try again later or contact our support directly." });
    },
  });

  const isFollowing = authUser && user ? authUser.follows.includes(parseInt(userId!, 10)) : false;

  const handleFollowAction = () => {
    if (!authUser) {
      addMessage({ tags: 'error', content: "You have to be logged in to follow Creators" });
    } else {
      followMutation.mutate(isFollowing);
    }
  };

  const handleReportSubmit = (reportData: { target_type: string; target_id: number; reason: string; description: string }) => {
    reportMutation.mutate({ ...reportData, target_type: reportData.target_type as TargetTypeEnum });
  };

  const conditionalS = (count: number, name: string) => {
    return count !== 1 ? `${name}s` : name;
  };

  if (isLoading ||authLoading) return <Spinner />;
  if (error || !user) return <NotFound />;

  return (
    <div className="bg-gray-900 text-white pb-12">
      {message && (
          <Messages 
            message={message}
            onClose={removeMessage}
          />
        )}
      {/* Banner Image */}
      <div className="h-32 bg-gradient-to-r from-blue-400 via-green-700 to-zinc-800"></div>
      
      {/* Profile Info */}
      <div className="relative p-4">
        {/* Profile Picture */}
        <div className="absolute -top-16 left-4">
          <img src={getMediaUrl(user.avatar) || '/default-account.svg'} alt="Profile" className="w-24 h-24 bg-zinc-600 rounded-full border-4 border-gray-900" />
        </div>
        
        {/* Action Buttons */}
        {authUser && user.id !== authUser?.id &&
        <div className="flex justify-between space-x-2 ml-20 sm:ml-32">
          <button 
            onClick={handleFollowAction}
            className="flex flex-row gap-1 items-center bg-white text-black px-4 py-1 rounded-full text-sm font-bold"
          >
            <FollowerIcon />{isFollowing ? 'Unfollow' : 'Follow'}
          </button>
         
          <Modal isOpen={reportModal} onClose={() => setReportModal(false)}>
            <ReportForm  onSubmit={handleReportSubmit} target={user} targetType="account"/>
            </Modal>
          <div className="absolute right-2 top-2 bg-gray-800 bg-opacity-40 hover:bg-opacity-60 rounded-lg">
            <ReportButton onClick={() => setReportModal(true)}/>
          </div>
        </div>
        }
   
        
        {/* User Info */}
        <div className="mt-8 flex flex-col gap-2">
          <div className='flex flex-row gap-8'>
            <h1 className="text-xl font-bold">@{user.username}</h1>
            {isFollowing && (
              <div className='border-2 border-zinc-600 rounded-md'>
                <span className="text-sm font-semibold self-center p-1">Followed</span>
              </div>
            )}
          </div>
          <p className="mt-2">{user.biography}</p>

          {/* User Rating */}
          <div className="mt-4 flex flex-col sm:flex-row items-center max-w-fit relative group gap-2 font-semibold">
              <div>Global Trust Score:</div>
              <div className='flex flex-row gap-2'>
                <span className="text-yellow-400">★ {Number(user?.average_rating || 0).toFixed(1)}</span>
                <span className="text-gray-400">({user.total_ratings} {conditionalS(user.total_ratings, "Peer Review")})</span>
              </div>
            <div className="invisible group-hover:visible absolute left-full ml-2 top-1/2 transform -translate-y-1/2 z-10">
              <ViewFullRating 
                soundness={user.average_soundness}
                significance={user.average_significance}
                novelty={user.average_novelty}
                clarity={user.average_clarity}
              />
            </div>
          </div>
          
          {/* User Appreciation */}
          <div className="mt-2 flex flex-col sm:flex-row items-center max-w-fit gap-2 font-semibold">
              <div>Community Appreciation:</div>
              <div className='flex flex-row gap-2'>
                <span className="text-indigo-400">♥ {Number(user?.total_appreciation_score || 0).toFixed(1)}</span>
              </div>
          </div>
          

          <div className='font-semibold text-zinc-400'>
            <span>active since {user.joined_date}</span>
          </div>
          
          {/* Rank */}
          {user.rank && user.score > 0 &&
            <div className="mt-4 flex flex-row gap-4 items-center font-semibold">
            <span className="">Rank: #{user.rank}</span>
            <span className="">Score: {user.score}</span>
          </div>
          }
          {/* User Statistics */}
          <div className="mt-4 flex flex-row flex-wrap gap-4 text-xs sm:text-sm font-semibold">
            <div className="flex items-center">
              <FollowerIcon />
              <span>{user.follower_count} {conditionalS(user.follower_count, "Follower")} </span>
            </div>
            <div className="flex items-center">
              <SavedIcon />
              <span>{user.total_saves} Saved {conditionalS(user.total_saves, "Node")} </span>
            </div>
            <div className="flex items-center">
              <FulfillmentIcon />
              <span>{user.total_fulfillments} {conditionalS(user.total_fulfillments, "Fulfillment")} </span>
            </div>
            <div className="flex items-center">
              <VisitsIcon />
              <span>{user.total_visits} {conditionalS(user.total_visits, "Visit")} </span>
            </div>
            <div className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="mr-2">
                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
              </svg>
              <span>{user.total_research_nodes} Research {conditionalS(user.total_research_nodes, "Node")}</span>
            </div>
          </div>
          
        </div>
      </div>
      
      {/* Active Agents */}
      {user.active_agents && user.active_agents.length > 0 && (
        <div className="max-w-6xl px-4 py-8">
          <h2 className="text-2xl font-bold text-gray-300 mb-6">Active Agents</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {user.active_agents.map((agent: ActiveAgent) => (
              <div key={agent.id} className="bg-slate-800 rounded-xl p-4 border border-slate-700 flex flex-col justify-between h-full">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-lg text-white">@{agent.name}</span>
                </div>
                <div className="text-sm text-gray-400 flex items-center">
                  Trust: <span className="text-orange-400 ml-1 font-semibold flex items-center gap-1">{Number(agent.orange_stars || 0).toFixed(2)} <StarIcon /></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <UserNodes userId={user.id} private={false}/>
    </div>
  );
};

export default User;

