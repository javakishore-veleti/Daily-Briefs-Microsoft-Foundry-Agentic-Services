import { Injectable, signal } from '@angular/core';
import { ChatMessage, ChatThread } from './chat.models';

const STORAGE_KEY = 'daily-briefs-portal-chats';

@Injectable({ providedIn: 'root' })
export class ChatStore {
  readonly threads = signal<ChatThread[]>(this.read());

  threadsFor(briefId: string): ChatThread[] {
    return this.threads()
      .filter((thread) => thread.briefId === briefId)
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
  }

  thread(id: string): ChatThread | undefined {
    return this.threads().find((item) => item.id === id);
  }

  create(briefId: string): ChatThread {
    const now = new Date().toISOString();
    const thread: ChatThread = {
      id: crypto.randomUUID(),
      briefId,
      title: 'New chat',
      sessionId: crypto.randomUUID(),
      messages: [],
      updatedAt: now,
    };
    this.threads.update((items) => [thread, ...items]);
    this.persist();
    return thread;
  }

  append(threadId: string, message: ChatMessage): void {
    this.threads.update((items) =>
      items.map((thread) => {
        if (thread.id !== threadId) {
          return thread;
        }
        const title =
          thread.messages.length === 0 && message.role === 'user'
            ? clip(message.text)
            : thread.title;
        return {
          ...thread,
          title,
          messages: [...thread.messages, message],
          updatedAt: message.createdAt,
        };
      }),
    );
    this.persist();
  }

  private read(): ChatThread[] {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    try {
      const parsed = JSON.parse(raw) as ChatThread[];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  private persist(): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this.threads()));
  }
}

function clip(text: string): string {
  const compact = text.replace(/\s+/g, ' ').trim();
  if (compact.length <= 42) {
    return compact || 'New chat';
  }
  return `${compact.slice(0, 42).trim()}…`;
}
