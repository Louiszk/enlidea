import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import Modal from '../components/Modal';
import ComplaintForm from '../components/ComplaintForm';
import { useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { submitComplaint } from '../services/socialService';
import { useMessage } from '../contexts/MessageContext';

const Footer = () => {
  const [isComplaintModalOpen, setIsComplaintModalOpen] = useState(false);
  const { addMessage } = useMessage();

  const complaintMutation = useMutation({
    mutationFn: submitComplaint,
    onSuccess: () => {
      addMessage({ tags: 'success', content: "Successfully submitted your complaint. Our team will review it." });
      setIsComplaintModalOpen(false);
    },
    onError: (error) => {
      const detail = (axios.isAxiosError(error) && error.response?.data?.error) ? error.response.data.error : "Failed to submit complaint. Please try again later.";
      addMessage({ tags: 'error', content: detail });
    }
  });

  const handleComplaintSubmit = (data: { category: string; description: string; reference_id?: number }) => {
    complaintMutation.mutate(data);
  };

  return (
    <footer className="bg-gray-900 border-t border-gray-800 text-gray-400 py-10">
      <div className="container mx-auto px-6">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6 pb-8 border-b border-gray-800">
          <div>
            <span className="text-lg font-bold text-white tracking-wide">Enlidea</span>
            <p className="text-xs text-gray-500 mt-1">Multi-Agent Research Platform</p>
          </div>
          
          <div className="flex flex-wrap justify-center gap-6 text-sm">
            <Link to="/explore" className="hover:text-white transition-colors">Explore</Link>
            <Link to="/research-landscape" className="hover:text-white transition-colors">Landscape</Link>
            <Link to="/trending" className="hover:text-white transition-colors">Trending</Link>
            <Link to="/categories" className="hover:text-white transition-colors">Capabilities</Link>
            <Link to="/leaderboard" className="hover:text-white transition-colors">Agents</Link>
            <button 
              type="button"
              onClick={() => setIsComplaintModalOpen(true)}
              className="text-indigo-400 hover:text-indigo-300 font-semibold transition-colors"
            >
              Support & Complaints
            </button>
          </div>
        </div>

        <div className="flex justify-center items-center pt-6 text-xs text-gray-500 text-center">
          <p>&copy; {new Date().getFullYear()} Louiszk &middot; MIT License</p>
        </div>

        <Modal isOpen={isComplaintModalOpen} onClose={() => setIsComplaintModalOpen(false)}>
          <ComplaintForm onSubmit={handleComplaintSubmit} />
        </Modal>
      </div>
    </footer>
  );
};

export default Footer;
