import React from 'react';
import { Brain, Sparkles } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="glass-card border-b border-white/10 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <Brain className="w-8 h-8 text-primary-600" />
              <Sparkles className="w-4 h-4 text-yellow-500 absolute -top-1 -right-1 animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Agentic Content Generator
              </h1>
              <p className="text-sm text-gray-600">
                Transform knowledge into engaging educational content
              </p>
            </div>
          </div>
          
          <div className="hidden md:flex items-center space-x-6 text-sm text-gray-600">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span>AI Agents Active</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span>Gemini AI Ready</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};