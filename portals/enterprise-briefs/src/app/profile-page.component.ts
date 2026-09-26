import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { UserApi } from './user-api.service';
import { UserStore } from './user-store.service';

@Component({
  selector: 'app-profile-page',
  templateUrl: './profile-page.component.html',
})
export class ProfilePageComponent implements OnInit {
  private readonly api = inject(UserApi);
  private readonly store = inject(UserStore);
  private readonly router = inject(Router);

  readonly name = signal('');
  readonly email = signal('');
  readonly phone = signal('');
  readonly password = signal('');
  readonly error = signal('');
  readonly notice = signal('');
  readonly busy = signal(false);

  ngOnInit(): void {
    const current = this.store.current();
    if (!current) {
      return;
    }
    this.name.set(current.name);
    this.email.set(current.email);
    this.phone.set(current.phone);
    this.api.profile(current.id).subscribe({
      next: (user) => {
        this.store.set(user);
        this.name.set(user.name);
        this.email.set(user.email);
        this.phone.set(user.phone);
      },
      error: (error: HttpErrorResponse) => this.error.set(httpDetail(error)),
    });
  }

  onInput(field: 'name' | 'email' | 'phone' | 'password', event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    if (field === 'name') {
      this.name.set(value);
    } else if (field === 'email') {
      this.email.set(value);
    } else if (field === 'phone') {
      this.phone.set(value);
    } else {
      this.password.set(value);
    }
  }

  save(): void {
    const current = this.store.current();
    if (!current || this.busy()) {
      return;
    }
    this.busy.set(true);
    this.error.set('');
    this.notice.set('');
    this.api
      .update(
        { ...current, name: this.name().trim(), email: this.email().trim(), phone: this.phone().trim() },
        this.password(),
      )
      .subscribe({
        next: (user) => {
          this.store.set(user);
          this.password.set('');
          this.notice.set('Profile saved.');
          this.busy.set(false);
        },
        error: (error: HttpErrorResponse) => {
          this.error.set(httpDetail(error));
          this.busy.set(false);
        },
      });
  }

  remove(): void {
    const current = this.store.current();
    if (!current || this.busy()) {
      return;
    }
    this.busy.set(true);
    this.api.remove(current.id).subscribe({
      next: () => {
        this.store.clear();
        void this.router.navigateByUrl('/signin');
      },
      error: (error: HttpErrorResponse) => {
        this.error.set(httpDetail(error));
        this.busy.set(false);
      },
    });
  }
}

function httpDetail(error: HttpErrorResponse): string {
  const body = error.error as { detail?: string } | null;
  if (body?.detail) {
    return body.detail;
  }
  if (error.status === 0) {
    return 'The middleware is not reachable at http://127.0.0.1:8000.';
  }
  return 'The request failed.';
}
