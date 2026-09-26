import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { UserApi } from './user-api.service';
import { UserStore } from './user-store.service';

type AuthMode = 'signin' | 'signup' | 'forgot';

@Component({
  selector: 'app-auth-page',
  imports: [RouterLink],
  templateUrl: './auth-page.component.html',
})
export class AuthPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(UserApi);
  private readonly store = inject(UserStore);

  readonly mode = signal<AuthMode>('signin');
  readonly name = signal('');
  readonly email = signal('');
  readonly phone = signal('');
  readonly password = signal('');
  readonly resetCode = signal('');
  readonly issuedCode = signal('');
  readonly notice = signal('');
  readonly error = signal('');
  readonly busy = signal(false);

  ngOnInit(): void {
    this.route.data.subscribe((data) => {
      const mode = data['mode'];
      const next = mode === 'signup' || mode === 'forgot' ? mode : 'signin';
      this.mode.set(next);
      this.error.set('');
      this.notice.set('');
      this.issuedCode.set('');
      if (next === 'signin') {
        this.email.set('enterprise-user');
        this.password.set('password');
      }
    });
  }

  onInput(field: 'name' | 'email' | 'phone' | 'password' | 'resetCode', event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    if (field === 'name') {
      this.name.set(value);
    } else if (field === 'email') {
      this.email.set(value);
    } else if (field === 'phone') {
      this.phone.set(value);
    } else if (field === 'password') {
      this.password.set(value);
    } else {
      this.resetCode.set(value);
    }
  }

  submit(): void {
    if (this.busy()) {
      return;
    }
    this.error.set('');
    this.busy.set(true);
    const mode = this.mode();
    if (mode === 'signup') {
      this.api.signup(this.email().trim(), this.password(), this.name().trim(), this.phone().trim()).subscribe({
        next: (user) => this.enter(user),
        error: (error: HttpErrorResponse) => this.fail(error),
      });
      return;
    }
    if (mode === 'forgot') {
      if (!this.issuedCode()) {
        this.api.forgotPassword(this.email().trim()).subscribe({
          next: (result) => {
            this.issuedCode.set(result.reset_code);
            this.notice.set(result.detail);
            this.busy.set(false);
          },
          error: (error: HttpErrorResponse) => this.fail(error),
        });
        return;
      }
      this.api.resetPassword(this.email().trim(), this.resetCode().trim(), this.password()).subscribe({
        next: (user) => this.enter(user),
        error: (error: HttpErrorResponse) => this.fail(error),
      });
      return;
    }
    this.api.signin(this.email().trim(), this.password()).subscribe({
      next: (user) => this.enter(user),
      error: (error: HttpErrorResponse) => this.fail(error),
    });
  }

  private enter(user: { id: string; name: string; email: string; phone: string; created_at?: string | null }): void {
    this.store.set(user);
    this.busy.set(false);
    void this.router.navigateByUrl('/daily-briefs-search');
  }

  private fail(error: HttpErrorResponse): void {
    this.busy.set(false);
    this.error.set(httpDetail(error));
  }
}

function httpDetail(error: HttpErrorResponse): string {
  const body = error.error as { detail?: string } | string | null;
  if (body && typeof body === 'object' && body.detail) {
    return body.detail;
  }
  if (typeof body === 'string' && body.trim()) {
    return body;
  }
  if (error.status === 0) {
    return 'The middleware is not reachable at http://127.0.0.1:8000.';
  }
  return 'The request failed.';
}
