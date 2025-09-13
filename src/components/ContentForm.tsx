import React, { useState } from 'react';
import { Send, Globe, Github, FileText, Type } from 'lucide-react';
import { ContentRequest } from '../types';

interface ContentFormProps {
  onSubmit: (request: ContentRequest) => void;
}

export const ContentForm: React.FC<ContentFormProps> = ({ onSubmit }) => {
  const [formData, setFormData] = useState<ContentRequest>({
    knowledgeSource: '',
    sourceType: 'website',
    contentType: 'tutorial',
    topic: '',
    targetAudience: 'intermediate',
    tone: 'conversational',
    constraints: {
      complexity: 'medium',
      length: 'medium'
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const sourceTypeIcons = {
    website: Globe,
    github: Github,
    document: FileText,
    text: Type
  };

  const contentTypeDescriptions = {
    youtube: 'Engaging video scripts with timing markers and visual cues',
    tutorial: 'Step-by-step guides with code examples and exercises',
    book: 'Comprehensive chapters with theory and practical applications',
    interactive: 'Quizzes, exercises, and hands-on learning experiences'
  };

  return (
    <div className="glass-card p-8 rounded-xl max-w-4xl mx-auto">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Generate Educational Content
        </h2>
        <p className="text-gray-600">
          Provide your knowledge source and preferences to generate high-quality educational content
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Knowledge Source Section */}
        <div className="space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
            <div className="w-6 h-6 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-primary-600 text-sm font-bold">1</span>
            </div>
            <span>Knowledge Source</span>
          </h3>

          <div className="grid md:grid-cols-4 gap-4">
            {Object.entries(sourceTypeIcons).map(([type, Icon]) => (
              <button
                key={type}
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, sourceType: type as any }))}
                className={`p-4 rounded-lg border-2 transition-all duration-200 ${
                  formData.sourceType === type
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }`}
              >
                <Icon className="w-6 h-6 mx-auto mb-2" />
                <span className="text-sm font-medium capitalize">{type}</span>
              </button>
            ))}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {formData.sourceType === 'website' && 'Website URL'}
              {formData.sourceType === 'github' && 'GitHub Repository URL'}
              {formData.sourceType === 'document' && 'Document Path or URL'}
              {formData.sourceType === 'text' && 'Text Content'}
            </label>
            {formData.sourceType === 'text' ? (
              <textarea
                value={formData.knowledgeSource}
                onChange={(e) => setFormData(prev => ({ ...prev, knowledgeSource: e.target.value }))}
                className="input-field h-32 resize-none"
                placeholder="Paste your text content here..."
                required
              />
            ) : (
              <input
                type="url"
                value={formData.knowledgeSource}
                onChange={(e) => setFormData(prev => ({ ...prev, knowledgeSource: e.target.value }))}
                className="input-field"
                placeholder={
                  formData.sourceType === 'website' ? 'https://example.com/docs' :
                  formData.sourceType === 'github' ? 'https://github.com/user/repo' :
                  'https://example.com/document.pdf'
                }
                required
              />
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Topic/Title (Optional)
            </label>
            <input
              type="text"
              value={formData.topic}
              onChange={(e) => setFormData(prev => ({ ...prev, topic: e.target.value }))}
              className="input-field"
              placeholder="e.g., React Hooks Tutorial, Machine Learning Basics"
            />
          </div>
        </div>

        {/* Content Type Section */}
        <div className="space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
            <div className="w-6 h-6 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-primary-600 text-sm font-bold">2</span>
            </div>
            <span>Content Type</span>
          </h3>

          <div className="grid md:grid-cols-2 gap-4">
            {Object.entries(contentTypeDescriptions).map(([type, description]) => (
              <button
                key={type}
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, contentType: type as any }))}
                className={`p-4 rounded-lg border-2 text-left transition-all duration-200 ${
                  formData.contentType === type
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <h4 className={`font-medium capitalize mb-2 ${
                  formData.contentType === type ? 'text-primary-700' : 'text-gray-900'
                }`}>
                  {type}
                </h4>
                <p className="text-sm text-gray-600">{description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Preferences Section */}
        <div className="space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
            <div className="w-6 h-6 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-primary-600 text-sm font-bold">3</span>
            </div>
            <span>Content Preferences</span>
          </h3>

          <div className="grid md:grid-cols-3 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Audience
              </label>
              <select
                value={formData.targetAudience}
                onChange={(e) => setFormData(prev => ({ ...prev, targetAudience: e.target.value as any }))}
                className="select-field"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tone & Style
              </label>
              <select
                value={formData.tone}
                onChange={(e) => setFormData(prev => ({ ...prev, tone: e.target.value as any }))}
                className="select-field"
              >
                <option value="conversational">Conversational</option>
                <option value="academic">Academic</option>
                <option value="storytelling">Storytelling</option>
                <option value="step-by-step">Step-by-step</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Content Length
              </label>
              <select
                value={formData.constraints.length}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  constraints: { ...prev.constraints, length: e.target.value as any }
                }))}
                className="select-field"
              >
                <option value="short">Short (5-10 min read)</option>
                <option value="medium">Medium (15-25 min read)</option>
                <option value="long">Long (30+ min read)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-6 border-t border-gray-200">
          <button
            type="submit"
            disabled={!formData.knowledgeSource}
            className="btn-primary w-full md:w-auto flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-5 h-5" />
            <span>Generate Content</span>
          </button>
        </div>
      </form>
    </div>
  );
};