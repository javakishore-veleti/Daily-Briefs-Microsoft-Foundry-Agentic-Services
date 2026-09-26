import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { WebSearchResponse } from './chat.models';

@Injectable({ providedIn: 'root' })
export class BriefApi {
  private readonly origin = 'http://127.0.0.1:8000';

  constructor(private readonly http: HttpClient) {}

  search(endpoint: string, query: string, sessionId: string): Observable<WebSearchResponse> {
    return this.http.post<WebSearchResponse>(`${this.origin}${endpoint}`, {
      query,
      session_id: sessionId,
    });
  }
}
