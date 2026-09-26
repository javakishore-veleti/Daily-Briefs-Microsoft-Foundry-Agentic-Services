export interface BriefMenu {
  id: string;
  label: string;
  description: string;
  endpoint: string;
}

export const BRIEF_MENUS: BriefMenu[] = [
  {
    id: 'web-search',
    label: 'Web Search',
    description: 'Ask a question and keep the thread.',
    endpoint: '/api/v1/daily-briefs/web-search',
  },
];

export function briefById(id: string): BriefMenu | undefined {
  return BRIEF_MENUS.find((menu) => menu.id === id);
}
