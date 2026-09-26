import { Injectable, signal } from '@angular/core';
import { SignedInUser } from './user.models';

const storageKey = 'enterprise-briefs-user';

@Injectable({ providedIn: 'root' })
export class UserStore {
  readonly current = signal<SignedInUser | null>(readUser());

  set(user: SignedInUser): void {
    sessionStorage.setItem(storageKey, JSON.stringify(user));
    this.current.set(user);
  }

  clear(): void {
    sessionStorage.removeItem(storageKey);
    this.current.set(null);
  }
}

function readUser(): SignedInUser | null {
  const raw = sessionStorage.getItem(storageKey);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as SignedInUser;
    if (!parsed.id) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}
