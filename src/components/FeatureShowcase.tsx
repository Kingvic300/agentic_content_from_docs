import React from 'react';
import { 
  Globe, 
  Github, 
  FileText, 
  Video, 
  BookOpen, 
  GraduationCap, 
  Zap,
  Target,
  Brain,
  CheckCircle
} from 'lucide-react';

export const FeatureShowcase: React.FC = () => {
  const features = [
    {
      icon: Globe,
      title: 'Web Scraping',
      description: 'Extract knowledge from websites with intelligent content filtering'
    },
    {
      icon: Github,
      title: 'GitHub Integration',
      description: 'Analyze repositories and documentation automatically'
    },
    {
      icon: Brain,
      title: 'AI Memory System',
      description: 'Semantic embeddings and relationship mapping for context'
    },
    {
      icon: Zap,
      title: 'Multi-Agent Workflow',
      description: 'Coordinated agents for ingestion, planning, and generation'
    }
  ];

  const contentTypes = [
    { icon: Video, label: 'YouTube Scripts', color: 'text-red-500' },
    { icon: BookOpen, label: 'Book Chapters', color: 'text-blue-500' },
    { icon: GraduationCap, label: 'Tutorials', color: 'text-green-500' },
    { icon: Target, label: 'Interactive Content', color: 'text-purple-500' }
  ];

  const workflow = [
    'Knowledge Ingestion',
    'Content Analysis',
    'Memory Building',
    'Structure Planning',
    'AI Generation',
    'Quality Validation'
  ];

  return (
    <div className="mb-12 space-y-12">
      {/* Hero Section */}
      <div className="text-center space-y-6">
        <h2 className="text-4xl font-bold text-gray-900 leading-tight">
          Transform Any Knowledge Source Into
          <span className="block text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-purple-600">
            Engaging Educational Content
          </span>
        </h2>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
          Our agentic AI system intelligently processes websites, GitHub repositories, and documents 
          to create high-quality tutorials, YouTube scripts, book chapters, and interactive learning materials.
        </p>
      </div>

      {/* Features Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
        {features.map((feature, index) => (
          <div 
            key={index}
            className="glass-card p-6 rounded-xl hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
          >
            <feature.icon className="w-10 h-10 text-primary-600 mb-4" />
            <h3 className="font-semibold text-gray-900 mb-2">{feature.title}</h3>
            <p className="text-gray-600 text-sm leading-relaxed">{feature.description}</p>
          </div>
        ))}
      </div>

      {/* Content Types */}
      <div className="glass-card p-8 rounded-xl">
        <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
          Generate Multiple Content Formats
        </h3>
        <div className="grid md:grid-cols-4 gap-6">
          {contentTypes.map((type, index) => (
            <div key={index} className="text-center space-y-3">
              <div className="mx-auto w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center">
                <type.icon className={`w-8 h-8 ${type.color}`} />
              </div>
              <h4 className="font-medium text-gray-900">{type.label}</h4>
            </div>
          ))}
        </div>
      </div>

      {/* Workflow */}
      <div className="glass-card p-8 rounded-xl">
        <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
          Intelligent Multi-Agent Workflow
        </h3>
        <div className="flex flex-wrap justify-center items-center gap-4">
          {workflow.map((step, index) => (
            <React.Fragment key={index}>
              <div className="flex items-center space-x-3 bg-gradient-to-r from-primary-50 to-purple-50 px-4 py-2 rounded-full">
                <CheckCircle className="w-5 h-5 text-primary-600" />
                <span className="font-medium text-gray-900">{step}</span>
              </div>
              {index < workflow.length - 1 && (
                <div className="w-8 h-0.5 bg-gradient-to-r from-primary-300 to-purple-300 hidden md:block"></div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
};