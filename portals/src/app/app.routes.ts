import { Routes } from '@angular/router';
import { BriefChatComponent } from './brief-chat.component';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'web-search' },
  { path: ':briefId', component: BriefChatComponent },
];
