import React, { useState } from 'react';

const ComplaintForm = ({ onSubmit }: { onSubmit: (data: any) => void }) => {
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [referenceId, setReferenceId] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ 
      category, 
      description, 
      reference_id: referenceId 
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-6 rounded-lg bg-zinc-900 border border-zinc-700 shadow-2xl">
      <div className="mb-4">
        <h2 className="text-2xl font-black text-white tracking-tighter uppercase">Submit a Complaint</h2>
        <p className="text-gray-400 text-sm">Our moderation team will review your case and respond shortly.</p>
      </div>

      <div>
        <label htmlFor="category" className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-1">
          Category
        </label>
        <select
          id="category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full bg-zinc-800 border border-zinc-700 text-white rounded-lg p-3 focus:outline-none focus:border-indigo-500 transition-colors"
          required
        >
          <option value="">Select Category</option>
          <option value="auto_kick_dispute">Auto-Kick Dispute</option>
          <option value="platform_issue">Platform Issue</option>
          <option value="transaction_issue">Transaction Issue</option>
          <option value="other">Other</option>
        </select>
      </div>

      <div>
        <label htmlFor="referenceId" className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-1">
          Reference ID (Optional)
        </label>
        <input
          id="referenceId"
          type="text"
          maxLength={100}
          value={referenceId}
          onChange={(e) => setReferenceId(e.target.value)}
          className="w-full bg-zinc-800 border border-zinc-700 text-white rounded-lg p-3 focus:outline-none focus:border-indigo-500 transition-colors"
          placeholder="e.g. Node ID or Report ID"
        />
      </div>

      <div>
        <label htmlFor="description" className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-1">
          Description
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={5}
          maxLength={5000}
          className="w-full bg-zinc-800 border border-zinc-700 text-white rounded-lg p-3 focus:outline-none focus:border-indigo-500 transition-colors"
          placeholder="Please describe the issue in detail..."
          required
        ></textarea>
      </div>

      <button
        type="submit"
        className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-black py-3 rounded-lg transition-all shadow-lg shadow-indigo-600/20 uppercase tracking-widest"
      >
        Submit Complaint
      </button>
    </form>
  );
};

export default ComplaintForm;
