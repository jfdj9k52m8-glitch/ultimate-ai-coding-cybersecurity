// API client + SSE stream parsing for the assistant backend.

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id?: number;
  role: "user" | "assistant";
  content: string;
  images: string[];
  skills?: string[];
  memoryNote?: string;
  error?: string;
}

export interface Memory {
  id: number;
  content: string;
  category: string;
  created_at: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  keywords: string[];
  always_on: boolean;
  enabled: boolean;
}

export interface Status {
  provider: string;
  base_url: string;
  reachable: boolean;
  detail: string;
  available_models: string[];
  model: string;
  vision_model: string;
  requested_context_tokens: number;
  model_max_context: number | null;
  effective_context_tokens: number;
  capabilities: string[];
}

export interface Settings {
  provider: string;
  base_url: string;
  model: string;
  vision_model: string;
  context_tokens: number;
  temperature: number;
  memory_extraction: boolean;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  status: () => fetch("/api/status").then((r) => json<Status>(r)),
  getSettings: () => fetch("/api/settings").then((r) => json<Settings>(r)),
  updateSettings: (update: Partial<Settings>) =>
    fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    }).then((r) => json<Settings>(r)),

  conversations: () =>
    fetch("/api/conversations").then((r) => json<Conversation[]>(r)),
  createConversation: () =>
    fetch("/api/conversations", { method: "POST" }).then((r) =>
      json<Conversation>(r),
    ),
  deleteConversation: (id: number) =>
    fetch(`/api/conversations/${id}`, { method: "DELETE" }).then((r) =>
      json<{ ok: boolean }>(r),
    ),
  messages: (id: number) =>
    fetch(`/api/conversations/${id}/messages`).then((r) => json<Message[]>(r)),

  memories: () => fetch("/api/memories").then((r) => json<Memory[]>(r)),
  addMemory: (content: string, category: string) =>
    fetch("/api/memories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, category }),
    }).then((r) => json<Memory>(r)),
  deleteMemory: (id: number) =>
    fetch(`/api/memories/${id}`, { method: "DELETE" }).then((r) =>
      json<{ ok: boolean }>(r),
    ),

  skills: () => fetch("/api/skills").then((r) => json<Skill[]>(r)),
  toggleSkill: (id: string, enabled: boolean) =>
    fetch(`/api/skills/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    }).then((r) => json<{ ok: boolean }>(r)),
};

export type ChatEvent =
  | { type: "conversation"; id: number }
  | { type: "meta"; skills: string[]; model: string }
  | { type: "token"; content: string }
  | {
      type: "memory";
      remembered: { content: string }[];
      forgotten: { content: string }[];
    }
  | { type: "error"; message: string }
  | { type: "done" };

export async function streamChat(
  body: { conversation_id: number | null; message: string; images: string[] },
  onEvent: (event: ChatEvent) => void,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      try {
        onEvent(JSON.parse(line.slice(5)) as ChatEvent);
      } catch {
        /* skip malformed frame */
      }
    }
  }
}
