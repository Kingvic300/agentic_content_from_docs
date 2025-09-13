export interface ContentRequest {
  knowledgeSource: string;
  sourceType: 'website' | 'github' | 'document' | 'text';
  contentType: 'youtube' | 'tutorial' | 'book' | 'interactive';
  topic?: string;
  targetAudience: 'beginner' | 'intermediate' | 'advanced';
  tone: 'conversational' | 'academic' | 'storytelling' | 'step-by-step';
  constraints: {
    wordCount?: number;
    complexity?: 'low' | 'medium' | 'high';
    length?: 'short' | 'medium' | 'long';
  };
}

export interface GeneratedContent {
  title: string;
  outline: string[];
  content: string;
  learningObjectives: string[];
  interactiveElements: string[];
  qualityMetrics: {
    accuracy: number;
    readability: number;
    engagement: number;
    completeness: number;
  };
}

export interface ProcessingStage {
  name: string;
  description: string;
  completed: boolean;
}