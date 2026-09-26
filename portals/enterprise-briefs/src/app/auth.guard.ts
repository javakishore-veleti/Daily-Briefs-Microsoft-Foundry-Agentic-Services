import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { UserStore } from './user-store.service';

export const authGuard: CanActivateFn = () => {
  const user = inject(UserStore).current();
  if (user) {
    return true;
  }
  return inject(Router).createUrlTree(['/signin']);
};

export const guestGuard: CanActivateFn = () => {
  const user = inject(UserStore).current();
  if (!user) {
    return true;
  }
  return inject(Router).createUrlTree(['/daily-briefs-search']);
};
