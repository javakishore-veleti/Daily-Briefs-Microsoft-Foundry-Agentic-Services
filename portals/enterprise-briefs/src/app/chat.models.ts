export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  sequence?: number;
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
  sequence: number;
  created_at: string | null;
  conversation_id: string;
}

export interface PromptGroup {
  id: string;
  prompt: string;
  responses: ChatMessage[];
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

export interface JoinerInfo {
  id: string;
  first_name: string;
  middle_name: string;
  last_name: string;
  email: string;
  contact_phone: string;
  contact_address: string;
  interviewed_by_employee_ids: string[];
  interviewed_by_employee_names: string[];
  official_role_name: string;
  internal_role_name: string;
  joining_official_role_name: string;
  salary_accepted_usd: number;
  joining_date: string;
  resumes: string;
  personal_interests: string;
  food_preferences: string;
}

export interface JoinerListResponse {
  joining_date: string;
  joiners: JoinerInfo[];
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
