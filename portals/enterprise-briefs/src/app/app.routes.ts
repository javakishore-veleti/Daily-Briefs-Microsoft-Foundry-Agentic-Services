import { Routes } from '@angular/router';
import { AuthPageComponent } from './auth-page.component';
import { authGuard, guestGuard } from './auth.guard';
import { BriefChatComponent } from './brief-chat.component';
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
      { path: ':briefId', component: BriefChatComponent },
    ],
  },
];
