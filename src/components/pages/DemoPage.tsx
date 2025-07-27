'use client';

import React from 'react';
import AgentChatPage from './AgentChatPage';

const DemoPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Agent Context Demo</h1>
          <p className="text-gray-600 mt-1">
            Test session management, chat functionality, and context management
          </p>
        </div>
      </div>
      <AgentChatPage />
    </div>
  );
};

export default DemoPage; 