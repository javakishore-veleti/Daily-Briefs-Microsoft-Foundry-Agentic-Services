export interface BriefMenu {
  id: string;
  label: string;
  description: string;
  endpoint: string;
}

export const BRIEF_MENUS: BriefMenu[] = [
  {
    id: 'daily-briefs-search',
    label: 'Daily Briefs Search',
    description: 'Searches the web first, then answers from what it finds.',
    endpoint: '/api/v1/daily-briefs/web-search',
  },
];

export function briefById(id: string): BriefMenu | undefined {
  return BRIEF_MENUS.find((menu) => menu.id === id);
}
