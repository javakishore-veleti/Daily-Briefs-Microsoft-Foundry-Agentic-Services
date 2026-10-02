import { HttpErrorResponse, HttpEventType, HttpResponse } from '@angular/common/http';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { briefById } from './briefs';
import { BriefApi } from './brief-api.service';
import { ChatStore } from './chat-store.service';
import { UserStore } from './user-store.service';
import {
  ChatHistoryListResponse,
  ChatHistorySessionResponse,
  ChatMessage,
  ChatThread,
  JoinerInfo,
  PromptGroup,
} from './chat.models';

const briefId = 'hr-daily-brief';
const pageSize = 10;

@Component({
  selector: 'app-hr-daily-brief',
  imports: [RouterLink],
  templateUrl: './hr-daily-brief.component.html',
  styleUrl: './hr-daily-brief.component.scss',
})
export class HrDailyBriefComponent implements OnInit, OnDestroy {
  @ViewChild('transcript') private transcript?: ElementRef<HTMLElement>;

  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly store = inject(ChatStore);
  private readonly users = inject(UserStore);
  private readonly api = inject(BriefApi);
  private readonly sanitizer = inject(DomSanitizer);

  readonly menu = briefById(briefId);
  readonly joiningDate = signal(localDate());
  readonly joiners = signal<JoinerInfo[]>([]);
  readonly joinerSkip = signal(0);
  readonly joinersHaveMore = signal(false);
  readonly listError = signal('');
  readonly selected = signal<JoinerInfo | undefined>(undefined);
  readonly detailError = signal('');
  readonly threads = signal<ChatThread[]>([]);
  readonly active = signal<ChatThread | undefined>(undefined);
  readonly draft = signal('');
  readonly sending = signal(false);
  readonly waitStatus = signal('');
  readonly waitSeconds = signal(0);
  readonly hasMore = signal(false);

  private historySkip = 0;
  private joinerId = '';
  private waitTimer = 0;

  constructor() {
    effect(() => {
      this.active();
      this.sending();
      this.waitStatus();
      queueMicrotask(() => this.scrollToEnd());
    });
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      this.joinerId = params.get('joinerId') ?? '';
      this.selected.set(undefined);
      this.detailError.set('');
      this.threads.set([]);
      this.active.set(undefined);
      this.historySkip = 0;
      this.hasMore.set(false);
      if (this.joinerId) {
        this.loadJoiner();
        this.loadHistory(false);
        return;
      }
      this.loadJoiners(0);
    });
  }

  onDate(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    if (!value) {
      return;
    }
    this.joiningDate.set(value);
    this.loadJoiners(0);
  }

  previousPage(): void {
    this.loadJoiners(Math.max(0, this.joinerSkip() - pageSize));
  }

  nextPage(): void {
    if (!this.joinersHaveMore()) {
      return;
    }
    this.loadJoiners(this.joinerSkip() + pageSize);
  }

  openJoiner(joiner: JoinerInfo): void {
    void this.router.navigate(['/hr-daily-brief', joiner.id]);
  }

  displayName(joiner: JoinerInfo): string {
    return [joiner.first_name, joiner.middle_name, joiner.last_name].filter(Boolean).join(' ');
  }

  money(value: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(
      value || 0,
    );
  }

  moreHistory(): void {
    this.loadHistory(true);
  }

  newChat(): void {
    if (!this.joinerId) {
      return;
    }
    const thread = this.store.create(this.chatBriefId());
    this.refresh(thread.id);
  }

  openChat(threadId: string): void {
    this.active.set(this.store.thread(threadId));
  }

  onDraft(event: Event): void {
    this.draft.set((event.target as HTMLTextAreaElement).value);
  }

  onComposerKey(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
  }

  joinerIdPresent(): boolean {
    return this.joinerId.length > 0;
  }

  isEmpty(): boolean {
    return this.groups().length === 0;
  }

  groups(): PromptGroup[] {
    const groups: PromptGroup[] = [];
    for (const item of this.active()?.messages ?? []) {
      if (item.role === 'user') {
        if (groups.some((group) => group.prompt === item.text)) {
          continue;
        }
        groups.push({ id: item.id, prompt: item.text, responses: [] });
        continue;
      }
      const current = groups[groups.length - 1];
      if (!current) {
        continue;
      }
      current.responses.push(item);
    }
    for (const group of groups) {
      group.responses.sort((left, right) => (left.sequence ?? 0) - (right.sequence ?? 0));
    }
    return groups;
  }

  send(): void {
    const text = this.draft().trim();
    if (!this.joinerId || !text || this.sending()) {
      return;
    }
    let thread = this.active();
    if (!thread) {
      thread = this.store.create(this.chatBriefId());
    }
    const threadId = thread.id;
    const existing = thread.messages.some((item) => item.role === 'user' && item.text === text);
    if (!existing) {
      this.store.append(threadId, message('user', text));
    }
    this.draft.set('');
    this.startWait();
    this.refresh(threadId);
    const sessionId = this.store.thread(threadId)?.sessionId ?? thread.sessionId;
    const userId = this.users.current()?.id ?? '';
    this.api.askHr(text, sessionId, userId, this.joinerId).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.Sent || event.type === HttpEventType.UploadProgress) {
          this.waitStatus.set('Server received your question. Waiting for the reply.');
          return;
        }
        if (!(event instanceof HttpResponse)) {
          return;
        }
        const response = event.body;
        if (!response) {
          this.finishWait(threadId, text, 'The server returned an empty reply.', true);
          return;
        }
        const sequence = nextSequence(this.store.thread(threadId)?.messages ?? [], text);
        this.store.appendResponse(threadId, text, {
          ...message('assistant', response.output_text),
          sequence,
          inputTokens: response.input_tokens,
          outputTokens: response.output_tokens,
          totalTokens: response.total_tokens,
        });
        this.stopWait();
        this.refresh(threadId);
        this.historySkip = 0;
        this.loadHistory(false);
      },
      error: (error: HttpErrorResponse) => {
        this.finishWait(threadId, text, errorMessage(error), true);
      },
    });
  }

  ngOnDestroy(): void {
    this.stopWait();
  }

  private startWait(): void {
    this.stopWait();
    this.sending.set(true);
    this.waitSeconds.set(0);
    this.waitStatus.set('Sending your question to the server.');
    const started = Date.now();
    this.waitTimer = window.setInterval(() => {
      this.waitSeconds.set(Math.floor((Date.now() - started) / 1000));
    }, 1000);
  }

  private finishWait(threadId: string, text: string, reply: string, failed: boolean): void {
    const sequence = nextSequence(this.store.thread(threadId)?.messages ?? [], text);
    this.store.appendResponse(threadId, text, {
      ...message('assistant', reply, failed),
      sequence,
    });
    this.stopWait();
    this.refresh(threadId);
  }

  private stopWait(): void {
    if (this.waitTimer) {
      window.clearInterval(this.waitTimer);
      this.waitTimer = 0;
    }
    this.sending.set(false);
    this.waitStatus.set('');
  }

  html(text: string): SafeHtml {
    const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const linked = escaped.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
    );
    return this.sanitizer.bypassSecurityTrustHtml(linked);
  }

  private loadJoiners(skip: number): void {
    const userId = this.users.current()?.id ?? '';
    if (!userId) {
      return;
    }
    this.listError.set('');
    this.api.joiners(this.joiningDate(), pageSize, skip, userId).subscribe({
      next: (response) => {
        this.joiners.set(response.joiners);
        this.joinerSkip.set(skip);
        this.joinersHaveMore.set(response.has_more);
      },
      error: (error: HttpErrorResponse) => {
        this.joiners.set([]);
        this.listError.set(errorMessage(error));
      },
    });
  }

  private loadJoiner(): void {
    const userId = this.users.current()?.id ?? '';
    if (!userId || !this.joinerId) {
      return;
    }
    this.api.joiner(this.joinerId, userId).subscribe({
      next: (joiner) => this.selected.set(joiner),
      error: (error: HttpErrorResponse) => this.detailError.set(errorMessage(error)),
    });
  }

  private loadHistory(append: boolean): void {
    const userId = this.users.current()?.id ?? '';
    if (!userId || !this.joinerId) {
      return;
    }
    const skip = append ? this.historySkip : 0;
    this.api.history(briefId, pageSize, skip, userId, this.joinerId).subscribe({
      next: (response) => this.applyHistory(response, append, skip),
    });
  }

  private applyHistory(response: ChatHistoryListResponse, append: boolean, skip: number): void {
    const scoped = this.chatBriefId();
    const incoming = response.sessions.map((session) => toThread(scoped, session));
    const active = this.active();
    let next = append ? [...this.store.threadsFor(scoped), ...incoming] : incoming;
    if (!append && active && !next.some((thread) => thread.sessionId === active.sessionId)) {
      next = [active, ...next];
    }
    if (active) {
      const match = next.find((thread) => thread.sessionId === active.sessionId);
      if (match && active.messages.length > match.messages.length) {
        match.messages = active.messages;
        match.title = active.title;
      }
    }
    this.store.replaceBrief(scoped, next);
    this.historySkip = skip + response.sessions.length;
    this.hasMore.set(response.has_more);
    this.threads.set(this.store.threadsFor(scoped));
    if (active) {
      const match = this.store.threadsFor(scoped).find((thread) => thread.sessionId === active.sessionId);
      this.active.set(match ?? active);
      return;
    }
    this.active.set(this.threads()[0]);
  }

  private refresh(activeId: string): void {
    this.threads.set(this.store.threadsFor(this.chatBriefId()));
    this.active.set(this.store.thread(activeId));
  }

  private chatBriefId(): string {
    return `${briefId}:${this.joinerId}`;
  }

  private scrollToEnd(): void {
    const node = this.transcript?.nativeElement;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }
}

function localDate(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

function toThread(scopedBriefId: string, session: ChatHistorySessionResponse): ChatThread {
  return {
    id: session.session_id,
    briefId: scopedBriefId,
    title: session.title || 'New chat',
    sessionId: session.session_id,
    updatedAt: session.updated_at ?? session.created_at ?? new Date().toISOString(),
    messages: session.messages.map((item) => ({
      id: item.id || crypto.randomUUID(),
      role: item.role === 'user' ? 'user' : 'assistant',
      text: item.message,
      sequence: item.sequence,
      createdAt: item.created_at ?? new Date().toISOString(),
    })),
  };
}

function message(role: 'user' | 'assistant', text: string, failed = false): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    text,
    createdAt: new Date().toISOString(),
    failed,
  };
}

function nextSequence(messages: ChatMessage[], promptText: string): number {
  const promptIndex = messages.findIndex((item) => item.role === 'user' && item.text === promptText);
  if (promptIndex < 0) {
    return 1;
  }
  let count = 0;
  for (let index = promptIndex + 1; index < messages.length; index += 1) {
    if (messages[index].role !== 'assistant') {
      break;
    }
    count += 1;
  }
  return count + 1;
}

function errorMessage(error: HttpErrorResponse): string {
  const detail = error.error?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }
  if (typeof error.error === 'string' && error.error.trim()) {
    return error.error;
  }
  if (error.status === 0) {
    return 'The middleware is not reachable at http://127.0.0.1:8000.';
  }
  return `HR Daily Brief failed (${error.status}).`;
}
