import React from 'react';
import { Brain, Loader2, CheckCircle, Clock } from 'lucide-react';

interface ProcessingStatusProps {
  stage: string;
}

export const ProcessingStatus: React.FC<ProcessingStatusProps> = ({ stage }) => {
  const stages = [
    'Ingesting knowledge source...',
    'Analyzing and chunking content...',
    'Building memory embeddings...',
    'Planning content structure...',
    'Generating content with Gemini AI...',
    'Validating quality and accuracy...',
    'Finalizing output...'
  ];

  const currentStageIndex = stages.indexOf(stage);

  return (
    <div className="glass-card p-8 rounded-xl max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <div className="relative inline-block">
          <Brain className="w-16 h-16 text-primary-600 animate-pulse-slow" />
          <div className="absolute -top-2 -right-2">
            <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
          </div>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mt-4 mb-2">
          AI Agents Working
        </h2>
        <p className="text-gray-600">
          Our multi-agent system is processing your request...
        </p>
      </div>

      <div className="space-y-4">
        {stages.map((stageText, index) => {
          const isCompleted = index < currentStageIndex;
          const isCurrent = index === currentStageIndex;
          const isPending = index > currentStageIndex;

          return (
            <div
              key={index}
              className={`flex items-center space-x-4 p-4 rounded-lg transition-all duration-300 ${
                isCurrent ? 'bg-primary-50 border border-primary-200' :
                isCompleted ? 'bg-green-50 border border-green-200' :
                'bg-gray-50 border border-gray-200'
              }`}
            >
              <div className="flex-shrink-0">
                {isCompleted && (
                  <CheckCircle className="w-6 h-6 text-green-600" />
                )}
                {isCurrent && (
                  <Loader2 className="w-6 h-6 text-primary-600 animate-spin" />
                )}
                {isPending && (
                  <Clock className="w-6 h-6 text-gray-400" />
                )}
              </div>
              
              <div className="flex-1">
                <p className={`font-medium ${
                  isCurrent ? 'text-primary-900' :
                  isCompleted ? 'text-green-900' :
                  'text-gray-500'
                }`}>
                  {stageText}
                </p>
              </div>

              <div className="flex-shrink-0">
                {isCompleted && (
                  <span className="text-xs font-medium text-green-600 bg-green-100 px-2 py-1 rounded-full">
                    Complete
                  </span>
                )}
                {isCurrent && (
                  <span className="text-xs font-medium text-primary-600 bg-primary-100 px-2 py-1 rounded-full">
                    Processing
                  </span>
                )}
                {isPending && (
                  <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                    Pending
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start space-x-3">
          <Brain className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <h4 className="font-medium text-blue-900 mb-1">Multi-Agent Workflow</h4>
            <p className="text-sm text-blue-700">
              Our specialized AI agents work together: Ingestion Agent extracts and processes content, 
              Memory Agent builds semantic relationships, Planning Agent creates structure, 
              Generation Agent produces content with Gemini AI, and Quality Agent validates output.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};