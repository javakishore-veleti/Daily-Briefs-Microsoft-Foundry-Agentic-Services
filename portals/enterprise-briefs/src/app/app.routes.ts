import { Routes } from '@angular/router';
import { AuthPageComponent } from './auth-page.component';
import { authGuard, guestGuard } from './auth.guard';
import { BriefChatComponent } from './brief-chat.component';
import { HrDailyBriefComponent } from './hr-daily-brief.component';
import { ProfilePageComponent } from './profile-page.component';
import { ShellComponent } from './shell.component';

export const routes: Routes = [
  { path: 'signin', component: AuthPageComponent, canActivate: [guestGuard], data: { mode: 'signin' } },
  { path: 'signup', component: AuthPageComponent, canActivate: [guestGuard], data: { mode: 'signup' } },
  {
    path: 'forgot-password',
    component: AuthPageComponent,
    canActivate: [guestGuard],
    data: { mode: 'forgot' },
  },
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'daily-briefs-search' },
      { path: 'profile', component: ProfilePageComponent },
      { path: 'hr-daily-brief', component: HrDailyBriefComponent },
      { path: 'hr-daily-brief/:joinerId', component: HrDailyBriefComponent },
      { path: ':briefId', component: BriefChatComponent },
    ],
  },
];
