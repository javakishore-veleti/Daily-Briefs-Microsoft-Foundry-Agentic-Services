export interface BriefMenu {
  id: string;
  label: string;
  description: string;
  endpoint: string;
  placeholder: string;
  pending: string;
}

export const BRIEF_MENUS: BriefMenu[] = [
  {
    id: 'daily-briefs-search',
    label: 'Daily Briefs Search',
    description: 'Searches the web first, then answers from what it finds.',
    endpoint: '/api/v1/daily-briefs/web-search',
    placeholder: 'Ask a question',
    pending: 'Searching…',
  },
  {
    id: 'weather-agent',
    label: 'Weather Agent',
    description: 'Answers weather questions with the OpenAPI weather tool.',
    endpoint: '/api/v1/daily-briefs/weather-info',
    placeholder: 'Ask about the weather',
    pending: 'Checking the weather…',
  },
];

export function briefById(id: string): BriefMenu | undefined {
  return BRIEF_MENUS.find((menu) => menu.id === id);
}
