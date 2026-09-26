import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ChatHistoryListResponse, WebSearchResponse } from './chat.models';

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

  history(brief: string, limit: number, skip: number): Observable<ChatHistoryListResponse> {
    return this.http.get<ChatHistoryListResponse>(`${this.origin}/api/v1/daily-briefs/chat-history`, {
      params: {
        brief,
        limit,
        skip,
      },
    });
  }
}
