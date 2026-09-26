import { HttpErrorResponse } from '@angular/common/http';
import { Component, ElementRef, OnInit, ViewChild, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { BriefMenu, briefById } from './briefs';
import { BriefApi } from './brief-api.service';
import { ChatStore } from './chat-store.service';
import { UserStore } from './user-store.service';
import { ChatHistoryListResponse, ChatHistorySessionResponse, ChatMessage, ChatThread, PromptGroup } from './chat.models';

@Component({
  selector: 'app-brief-chat',
  imports: [RouterLink],
  templateUrl: './brief-chat.component.html',
  styleUrl: './brief-chat.component.scss',
})
export class BriefChatComponent implements OnInit {
  @ViewChild('transcript') private transcript?: ElementRef<HTMLElement>;

  private readonly route = inject(ActivatedRoute);
  private readonly store = inject(ChatStore);
  private readonly users = inject(UserStore);
  private readonly api = inject(BriefApi);
  private readonly sanitizer = inject(DomSanitizer);

  readonly menu = signal<BriefMenu | undefined>(undefined);
  readonly threads = signal<ChatThread[]>([]);
  readonly active = signal<ChatThread | undefined>(undefined);
  readonly draft = signal('');
  readonly sending = signal(false);
  readonly hasMore = signal(false);

  private historySkip = 0;
  private readonly pageSize = 10;

  constructor() {
    effect(() => {
      this.active();
      this.sending();
      queueMicrotask(() => this.scrollToEnd());
    });
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      const briefId = params.get('briefId') ?? '';
      const menu = briefById(briefId);
      this.menu.set(menu);
      if (!menu) {
        return;
      }
      this.historySkip = 0;
      this.hasMore.set(false);
      this.threads.set([]);
      this.active.set(undefined);
      this.loadHistory(false);
    });
  }

  moreHistory(): void {
    this.loadHistory(true);
  }

  newChat(): void {
    const menu = this.menu();
    if (!menu) {
      return;
    }
    const thread = this.store.create(menu.id);
    this.refresh(thread.id);
  }

  openChat(threadId: string): void {
    this.active.set(this.store.thread(threadId));
  }

  onDraft(event: Event): void {
    const target = event.target as HTMLTextAreaElement;
    this.draft.set(target.value);
  }

  onComposerKey(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
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
    const menu = this.menu();
    const text = this.draft().trim();
    if (!menu || !text || this.sending()) {
      return;
    }
    let thread = this.active();
    if (!thread) {
      thread = this.store.create(menu.id);
    }
    const threadId = thread.id;
    const existing = thread.messages.some((item) => item.role === 'user' && item.text === text);
    if (!existing) {
      this.store.append(threadId, message('user', text));
    }
    this.draft.set('');
    this.sending.set(true);
    this.refresh(threadId);
    const sessionId = this.store.thread(threadId)?.sessionId ?? thread.sessionId;
    const userId = this.users.current()?.id ?? '';
    this.api.search(menu.endpoint, text, sessionId, userId).subscribe({
      next: (response) => {
        const sequence = nextSequence(this.store.thread(threadId)?.messages ?? [], text);
        this.store.appendResponse(threadId, text, {
          ...message('assistant', response.output_text),
          sequence,
          inputTokens: response.input_tokens,
          outputTokens: response.output_tokens,
          totalTokens: response.total_tokens,
        });
        this.sending.set(false);
        this.refresh(threadId);
        this.historySkip = 0;
        this.loadHistory(false);
      },
      error: (error: HttpErrorResponse) => {
        const sequence = nextSequence(this.store.thread(threadId)?.messages ?? [], text);
        this.store.appendResponse(threadId, text, {
          ...message('assistant', errorMessage(error, menu.label), true),
          sequence,
        });
        this.sending.set(false);
        this.refresh(threadId);
      },
    });
  }

  html(text: string): SafeHtml {
    const escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    const linked = escaped.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
    );
    return this.sanitizer.bypassSecurityTrustHtml(linked);
  }

  private loadHistory(append: boolean): void {
    const menu = this.menu();
    if (!menu) {
      return;
    }
    const userId = this.users.current()?.id ?? '';
    if (!userId) {
      return;
    }
    const skip = append ? this.historySkip : 0;
    this.api.history(menu.id, this.pageSize, skip, userId).subscribe({
      next: (response) => this.applyHistory(menu.id, response, append, skip),
    });
  }

  private applyHistory(briefId: string, response: ChatHistoryListResponse, append: boolean, skip: number): void {
    const incoming = response.sessions.map((session) => toThread(briefId, session));
    const active = this.active();
    let next = append ? [...this.store.threadsFor(briefId), ...incoming] : incoming;
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
    this.store.replaceBrief(briefId, next);
    this.historySkip = skip + response.sessions.length;
    this.hasMore.set(response.has_more);
    this.threads.set(this.store.threadsFor(briefId));
    if (active) {
      const match = this.store.threadsFor(briefId).find((thread) => thread.sessionId === active.sessionId);
      this.active.set(match ?? active);
      return;
    }
    this.active.set(this.threads()[0]);
  }

  private refresh(activeId: string): void {
    const menu = this.menu();
    if (!menu) {
      return;
    }
    this.threads.set(this.store.threadsFor(menu.id));
    this.active.set(this.store.thread(activeId));
  }

  private scrollToEnd(): void {
    const node = this.transcript?.nativeElement;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }
}

function toThread(briefId: string, session: ChatHistorySessionResponse): ChatThread {
  return {
    id: session.session_id,
    briefId,
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

function errorMessage(error: HttpErrorResponse, label: string): string {
  if (typeof error.error === 'string' && error.error.trim()) {
    return error.error;
  }
  if (error.status === 0) {
    return 'The middleware is not reachable at http://127.0.0.1:8000.';
  }
  return `${label} failed (${error.status}).`;
}
