import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ForgotPasswordResult, SignedInUser } from './user.models';

@Injectable({ providedIn: 'root' })
export class UserApi {
  private readonly origin = 'http://127.0.0.1:8000';

  constructor(private readonly http: HttpClient) {}

  signup(email: string, password: string, name: string, phone: string): Observable<SignedInUser> {
    return this.http.post<SignedInUser>(`${this.origin}/api/v1/daily-briefs/users/signup`, {
      email,
      password,
      name,
      phone,
    });
  }

  signin(email: string, password: string): Observable<SignedInUser> {
    return this.http.post<SignedInUser>(`${this.origin}/api/v1/daily-briefs/users/signin`, {
      email,
      password,
    });
  }

  forgotPassword(email: string): Observable<ForgotPasswordResult> {
    return this.http.post<ForgotPasswordResult>(`${this.origin}/api/v1/daily-briefs/users/forgot-password`, {
      email,
    });
  }

  resetPassword(email: string, resetCode: string, password: string): Observable<SignedInUser> {
    return this.http.post<SignedInUser>(`${this.origin}/api/v1/daily-briefs/users/reset-password`, {
      email,
      reset_code: resetCode,
      password,
    });
  }

  profile(userId: string): Observable<SignedInUser> {
    return this.http.get<SignedInUser>(`${this.origin}/api/v1/daily-briefs/users/${userId}`);
  }

  update(user: SignedInUser, password: string): Observable<SignedInUser> {
    return this.http.put<SignedInUser>(`${this.origin}/api/v1/daily-briefs/users/${user.id}`, {
      name: user.name,
      email: user.email,
      phone: user.phone,
      password,
    });
  }

  remove(userId: string): Observable<SignedInUser> {
    return this.http.delete<SignedInUser>(`${this.origin}/api/v1/daily-briefs/users/${userId}`);
  }
}
