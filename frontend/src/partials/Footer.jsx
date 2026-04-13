import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import Modal from '../components/Modal';
import ComplaintForm from '../components/ComplaintForm';
import { useMutation } from '@tanstack/react-query';
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
      const detail = error.response?.data?.error || "Failed to submit complaint. Please try again later.";
      addMessage({ tags: 'error', content: detail });
    }
  });

  const handleComplaintSubmit = (data) => {
    complaintMutation.mutate(data);
  };

  return (
    <footer className="bg-gray-800 text-gray-300 py-8" style={{ height: "365px" }}>
      <div className="container mx-auto px-4">
        <div className="flex flex-col items-center">
          <div className="mb-4">
            <p className="text-sm">&copy; Enlidea 2024</p>
          </div>
          
          <nav className="mb-6">
            <ul className="flex flex-wrap justify-center space-x-4 text-sm">
              <li><Link to="#" className="hover:text-white">FAQ</Link></li>
              <li><Link to="#" className="hover:text-white">Contact</Link></li>
              <li><Link to="#" className="hover:text-white">Changelog</Link></li>
              <li><Link to="#" className="hover:text-white">Blog</Link></li>
              <li><Link to="#" className="hover:text-white">Privacy</Link></li>
              <li><Link to="#" className="hover:text-white">Terms</Link></li>
              <li><Link to="#" className="hover:text-white text-orange-400 font-bold" onClick={() => setIsComplaintModalOpen(true)}>File a Complaint / Support</Link></li>
            </ul>
          </nav>

          <Modal isOpen={isComplaintModalOpen} onClose={() => setIsComplaintModalOpen(false)}>
            <ComplaintForm onSubmit={handleComplaintSubmit} />
          </Modal>
          
          <div className="flex space-x-4 mb-6">
            <Link to="#" className="hover:text-white">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
              </svg>
            </Link>
            <Link to="#" className="hover:text-white">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
            </Link>
          </div>
          
          <div className="grid grid-cols-2 gap-8 text-sm">
            <div>
              <h3 className="font-bold mb-2 uppercase">Pages</h3>
              <ul className="space-y-1">
              </ul>
            </div>
            <div>
              <h3 className="font-bold mb-2 uppercase">Popular Categories</h3>
              <ul className="space-y-1">
              </ul>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
