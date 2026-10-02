import { HttpClient, HttpEvent } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ChatHistoryListResponse, JoinerInfo, JoinerListResponse, HrFoundryMemoryClearResponse, HrSampleDatasetBulkPopulateResponse, HrSampleDatasetStatusResponse, WebSearchResponse } from './chat.models';

@Injectable({ providedIn: 'root' })
export class BriefApi {
  private readonly origin = 'http://127.0.0.1:8000';

  constructor(private readonly http: HttpClient) {}

  search(endpoint: string, query: string, sessionId: string, userId: string): Observable<WebSearchResponse> {
    return this.http.post<WebSearchResponse>(`${this.origin}${endpoint}`, {
      query,
      session_id: sessionId,
      user_id: userId,
    });
  }

  history(
    brief: string,
    limit: number,
    skip: number,
    userId: string,
    joinerInfoId = '',
  ): Observable<ChatHistoryListResponse> {
    const params: Record<string, string | number> = {
      brief,
      limit,
      skip,
      user_id: userId,
    };
    if (joinerInfoId) {
      params['joiner_info_id'] = joinerInfoId;
    }
    return this.http.get<ChatHistoryListResponse>(`${this.origin}/api/v1/daily-briefs/chat-history`, {
      params,
    });
  }

  joiners(
    joiningDateFrom: string,
    joiningDateTo: string,
    limit: number,
    skip: number,
    userId: string,
  ): Observable<JoinerListResponse> {
    return this.http.get<JoinerListResponse>(`${this.origin}/api/v1/daily-briefs/joiners`, {
      params: {
        joining_date_from: joiningDateFrom,
        joining_date_to: joiningDateTo,
        limit,
        skip,
        user_id: userId,
      },
    });
  }

  joiner(joinerInfoId: string, userId: string): Observable<JoinerInfo> {
    return this.http.get<JoinerInfo>(`${this.origin}/api/v1/daily-briefs/joiners/${joinerInfoId}`, {
      params: { user_id: userId },
    });
  }

  hrSampleDatasetStatus(userId: string): Observable<HrSampleDatasetStatusResponse> {
    return this.http.get<HrSampleDatasetStatusResponse>(`${this.origin}/api/v1/daily-briefs/hr-sample-dataset`, {
      params: { user_id: userId },
    });
  }

  populateHrJoiners(userId: string, seedMemory = false): Observable<HrSampleDatasetBulkPopulateResponse> {
    return this.http.post<HrSampleDatasetBulkPopulateResponse>(
      `${this.origin}/api/v1/daily-briefs/hr-sample-dataset/populate-bulk`,
      {},
      {
        params: {
          user_id: userId,
          seed_memory: seedMemory ? 'true' : 'false',
        },
      },
    );
  }

  clearFoundryMemory(userId: string): Observable<HrFoundryMemoryClearResponse> {
    return this.http.post<HrFoundryMemoryClearResponse>(
      `${this.origin}/api/v1/daily-briefs/hr-sample-dataset/clear-foundry-memory`,
      {},
      {
        params: { user_id: userId },
      },
    );
  }

  askHr(query: string, sessionId: string, userId: string, joinerInfoId: string): Observable<HttpEvent<WebSearchResponse>> {
    return this.http.post<WebSearchResponse>(
      `${this.origin}/api/v1/daily-briefs/hr-assistant`,
      {
        query,
        session_id: sessionId,
        user_id: userId,
        joiner_info_id: joinerInfoId,
      },
      { observe: 'events', reportProgress: true },
    );
  }
}
