import React, { useState } from 'react';

export const ReportButton = ({ onClick }) => (
    <button
      onClick={onClick}
      className="p-2 text-gray-500 hover:text-red-500 focus:outline-none"
      aria-label="Report"
      title='Report'
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    </button>
  );

  export const ReportForm = ({ onSubmit, target, targetType, nodeId }) => {
    const [reason, setReason] = useState('');
    const [description, setDescription] = useState('');
  
    const handleSubmit = (e) => {
      e.preventDefault();
      onSubmit({ 
        reason, 
        description, 
        target_type: targetType, 
        target_id: target.id,
        node_id: nodeId
      });
    };
  
    return (
      <form onSubmit={handleSubmit} className="space-y-4 p-6 rounded-lg">
        <h2 className="text-xl font-bold text-white">Report {targetType}: {target.title || target.name || target.username}</h2>
        <div>
          <label htmlFor="reason" className="block text-sm font-medium text-gray-300">
            Reason
          </label>
          <select
            id="reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 text-white shadow-sm focus:border-indigo-500 focus:ring focus:ring-indigo-500 focus:ring-opacity-50"
            required
          >
            <option value="">Select a reason</option>
            <option value="spam">Spam</option>
            <option value="harassment">Harassment</option>
            <option value="inappropriate">Inappropriate Content</option>
            <option value="plagiarism_or_copyright">Plagiarism or Copyright</option>
            <option value="malicious_activity">Malicious Activity</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-300">
            Description
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            maxLength={5000}
            className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 text-white shadow-sm focus:border-indigo-500 focus:ring focus:ring-indigo-500 focus:ring-opacity-50"
            placeholder="Please provide more details about the issue..."
            required
          ></textarea>
        </div>
        <button
          type="submit"
          className="w-full px-4 py-2 text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-gray-800"
        >
          Submit Report
        </button>
      </form>
    );
  };
