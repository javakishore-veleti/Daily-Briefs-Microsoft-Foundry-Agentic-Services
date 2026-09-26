import { HttpErrorResponse } from '@angular/common/http';
import { Component, ElementRef, OnInit, ViewChild, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { BriefMenu, briefById } from './briefs';
import { BriefApi } from './brief-api.service';
import { ChatStore } from './chat-store.service';
import { ChatMessage, ChatThread } from './chat.models';

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
  private readonly api = inject(BriefApi);
  private readonly sanitizer = inject(DomSanitizer);

  readonly menu = signal<BriefMenu | undefined>(undefined);
  readonly threads = signal<ChatThread[]>([]);
  readonly active = signal<ChatThread | undefined>(undefined);
  readonly draft = signal('');
  readonly sending = signal(false);

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
      const threads = this.store.threadsFor(menu.id);
      this.threads.set(threads);
      this.active.set(threads[0]);
    });
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
    const thread = this.active();
    return !thread || thread.messages.length === 0;
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
    this.store.append(threadId, message('user', text));
    this.draft.set('');
    this.sending.set(true);
    this.refresh(threadId);
    const sessionId = this.store.thread(threadId)?.sessionId ?? thread.sessionId;
    this.api.search(menu.endpoint, text, sessionId).subscribe({
      next: (response) => {
        this.store.append(threadId, {
          ...message('assistant', response.output_text),
          inputTokens: response.input_tokens,
          outputTokens: response.output_tokens,
          totalTokens: response.total_tokens,
        });
        this.sending.set(false);
        this.refresh(threadId);
      },
      error: (error: HttpErrorResponse) => {
        this.store.append(
          threadId,
          message('assistant', errorMessage(error), true),
        );
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

function message(role: 'user' | 'assistant', text: string, failed = false): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    text,
    createdAt: new Date().toISOString(),
    failed,
  };
}

function errorMessage(error: HttpErrorResponse): string {
  if (typeof error.error === 'string' && error.error.trim()) {
    return error.error;
  }
  if (error.status === 0) {
    return 'The middleware is not reachable at http://127.0.0.1:8000.';
  }
  return `The search failed (${error.status}).`;
}
