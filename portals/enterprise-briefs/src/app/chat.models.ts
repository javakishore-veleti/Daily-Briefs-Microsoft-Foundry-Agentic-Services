export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  createdAt: string;
  inputTokens?: number;
  outputTokens?: number;
  totalTokens?: number;
  failed?: boolean;
}

export interface ChatThread {
  id: string;
  briefId: string;
  title: string;
  sessionId: string;
  messages: ChatMessage[];
  updatedAt: string;
}

export interface ChatHistoryMessageResponse {
  id: string;
  role: string;
  message: string;
  created_at: string | null;
  conversation_id: string;
}

export interface ChatHistorySessionResponse {
  session_id: string;
  conversation_id: string;
  title: string;
  created_at: string | null;
  updated_at: string | null;
  messages: ChatHistoryMessageResponse[];
}

export interface ChatHistoryListResponse {
  sessions: ChatHistorySessionResponse[];
  has_more: boolean;
}

export interface WebSearchResponse {
  output_text: string;
  conversation_id: string;
  response_id: string;
  model: string;
  status: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cached_tokens: number;
  reasoning_tokens: number;
}
