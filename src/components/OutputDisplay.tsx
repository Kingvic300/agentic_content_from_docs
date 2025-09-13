import React, { useState } from 'react';
import { 
  Download, 
  Copy, 
  RefreshCw, 
  CheckCircle, 
  Target, 
  BarChart3,
  BookOpen,
  List,
  FileText,
  Zap
} from 'lucide-react';
import { GeneratedContent } from '../types';

interface OutputDisplayProps {
  content: GeneratedContent;
  onReset: () => void;
}

export const OutputDisplay: React.FC<OutputDisplayProps> = ({ content, onReset }) => {
  const [activeTab, setActiveTab] = useState<'content' | 'outline' | 'objectives' | 'metrics'>('content');
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([
      `# ${content.title}\n\n`,
      `## Outline\n${content.outline.map(item => `- ${item}`).join('\n')}\n\n`,
      `## Learning Objectives\n${content.learningObjectives.map(obj => `- ${obj}`).join('\n')}\n\n`,
      `## Content\n${content.content}\n\n`,
      content.interactiveElements.length > 0 ? `## Interactive Elements\n${content.interactiveElements.map(elem => `- ${elem}`).join('\n')}\n\n` : '',
      `## Quality Metrics\n`,
      `- Accuracy: ${content.qualityMetrics.accuracy}%\n`,
      `- Readability: ${content.qualityMetrics.readability}%\n`,
      `- Engagement: ${content.qualityMetrics.engagement}%\n`,
      `- Completeness: ${content.qualityMetrics.completeness}%\n`
    ].join(''), { type: 'text/markdown' });
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${content.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const tabs = [
    { id: 'content', label: 'Content', icon: FileText },
    { id: 'outline', label: 'Outline', icon: List },
    { id: 'objectives', label: 'Objectives', icon: Target },
    { id: 'metrics', label: 'Quality', icon: BarChart3 }
  ];

  const getQualityColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-100';
    if (score >= 75) return 'text-blue-600 bg-blue-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-card p-6 rounded-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between space-y-4 md:space-y-0">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              {content.title}
            </h2>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <div className="flex items-center space-x-1">
                <CheckCircle className="w-4 h-4 text-green-500" />
                <span>Generated Successfully</span>
              </div>
              <div className="flex items-center space-x-1">
                <BarChart3 className="w-4 h-4 text-blue-500" />
                <span>Quality Score: {Math.round((content.qualityMetrics.accuracy + content.qualityMetrics.readability + content.qualityMetrics.engagement + content.qualityMetrics.completeness) / 4)}%</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={handleCopy}
              className="btn-secondary flex items-center space-x-2"
            >
              {copied ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              <span>{copied ? 'Copied!' : 'Copy'}</span>
            </button>
            <button
              onClick={handleDownload}
              className="btn-secondary flex items-center space-x-2"
            >
              <Download className="w-4 h-4" />
              <span>Download</span>
            </button>
            <button
              onClick={onReset}
              className="btn-primary flex items-center space-x-2"
            >
              <RefreshCw className="w-4 h-4" />
              <span>New Content</span>
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="glass-card rounded-xl overflow-hidden">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-4 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'content' && (
            <div className="space-y-4">
              <div className="prose max-w-none">
                <pre className="whitespace-pre-wrap text-sm leading-relaxed text-gray-800 bg-gray-50 p-6 rounded-lg border">
                  {content.content}
                </pre>
              </div>
              
              {content.interactiveElements.length > 0 && (
                <div className="mt-8 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                  <h4 className="font-medium text-purple-900 mb-3 flex items-center space-x-2">
                    <Zap className="w-4 h-4" />
                    <span>Interactive Elements</span>
                  </h4>
                  <ul className="space-y-2">
                    {content.interactiveElements.map((element, index) => (
                      <li key={index} className="text-sm text-purple-700 flex items-center space-x-2">
                        <div className="w-1.5 h-1.5 bg-purple-400 rounded-full"></div>
                        <span>{element}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {activeTab === 'outline' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                <BookOpen className="w-5 h-5 text-primary-600" />
                <span>Content Structure</span>
              </h3>
              <div className="space-y-3">
                {content.outline.map((item, index) => (
                  <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                    <div className="w-6 h-6 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-primary-600 text-xs font-bold">{index + 1}</span>
                    </div>
                    <span className="text-gray-800 leading-relaxed">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'objectives' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                <Target className="w-5 h-5 text-green-600" />
                <span>Learning Objectives</span>
              </h3>
              <div className="space-y-3">
                {content.learningObjectives.map((objective, index) => (
                  <div key={index} className="flex items-start space-x-3 p-3 bg-green-50 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-800 leading-relaxed">{objective}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'metrics' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                <BarChart3 className="w-5 h-5 text-blue-600" />
                <span>Quality Assessment</span>
              </h3>
              
              <div className="grid md:grid-cols-2 gap-6">
                {Object.entries(content.qualityMetrics).map(([metric, score]) => (
                  <div key={metric} className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-900 capitalize">
                        {metric.replace(/([A-Z])/g, ' $1').trim()}
                      </span>
                      <span className={`px-2 py-1 rounded-full text-sm font-medium ${getQualityColor(score)}`}>
                        {score}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-500 ${
                          score >= 90 ? 'bg-green-500' :
                          score >= 75 ? 'bg-blue-500' :
                          score >= 60 ? 'bg-yellow-500' :
                          'bg-red-500'
                        }`}
                        style={{ width: `${score}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="font-medium text-blue-900 mb-2">Quality Assessment Notes</h4>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• Content has been validated by our Quality Agent</li>
                  <li>• Technical accuracy verified through AI analysis</li>
                  <li>• Readability optimized for target audience</li>
                  <li>• Engagement elements strategically placed</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};