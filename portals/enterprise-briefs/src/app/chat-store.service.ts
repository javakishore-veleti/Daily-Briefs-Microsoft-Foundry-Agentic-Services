import { Injectable, signal } from '@angular/core';
import { ChatMessage, ChatThread } from './chat.models';

@Injectable({ providedIn: 'root' })
export class ChatStore {
  readonly threads = signal<ChatThread[]>([]);

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
    return thread;
  }

  appendResponse(threadId: string, promptText: string, message: ChatMessage): void {
    this.threads.update((items) =>
      items.map((thread) => {
        if (thread.id !== threadId) {
          return thread;
        }
        const messages = [...thread.messages];
        const promptIndex = messages.findIndex((item) => item.role === 'user' && item.text === promptText);
        if (promptIndex < 0) {
          messages.push(message);
        } else {
          let insertAt = promptIndex + 1;
          while (insertAt < messages.length && messages[insertAt].role === 'assistant') {
            insertAt += 1;
          }
          messages.splice(insertAt, 0, message);
        }
        return { ...thread, messages, updatedAt: message.createdAt };
      }),
    );
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
  }

  replaceBrief(briefId: string, threads: ChatThread[]): void {
    this.threads.update((items) => [
      ...threads,
      ...items.filter((item) => item.briefId !== briefId),
    ]);
  }
}

function clip(text: string): string {
  const compact = text.replace(/\s+/g, ' ').trim();
  if (compact.length <= 42) {
    return compact || 'New chat';
  }
  return `${compact.slice(0, 42).trim()}…`;
}
