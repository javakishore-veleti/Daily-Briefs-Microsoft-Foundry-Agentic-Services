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
  joining_date_from: string;
  joining_date_to: string;
  joiners: JoinerInfo[];
  has_more: boolean;
  total: number;
  limit: number;
  skip: number;
}

export interface HrSampleDatasetJoineeStatus {
  folder: string;
  display_name: string;
  email: string;
  joiner_info_id: string;
  mongo_populated: boolean;
  memory_populated: boolean;
  joining_date: string;
}

export interface HrSampleDatasetStatusResponse {
  dataset_path: string;
  joinee_count: number;
  populated: boolean;
  mongo_populated: boolean;
  memory_populated: boolean;
  populated_at: string;
  joinees: HrSampleDatasetJoineeStatus[];
  bulk_target_count: number;
  bulk_span_days: number;
  bulk_mongo_count: number;
  bulk_populated: boolean;
  bulk_memory_seeded: boolean;
  bulk_populated_at: string;
}

export interface HrSampleDatasetPopulateResponse {
  message: string;
  status: HrSampleDatasetStatusResponse;
  created?: number;
  skipped?: number;
  memory_seeded?: number;
}

export interface HrSampleDatasetBulkPopulateResponse {
  message: string;
  status: HrSampleDatasetStatusResponse;
  created: number;
  skipped: number;
  memory_seeded: number;
  target_count: number;
  span_days: number;
  seed_memory: boolean;
}

export interface HrFoundryMemoryClearResponse {
  message: string;
  status: HrSampleDatasetStatusResponse;
  memory_store_name: string;
  cleared: boolean;
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
