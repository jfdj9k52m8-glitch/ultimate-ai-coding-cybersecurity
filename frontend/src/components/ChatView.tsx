import {
  ClipboardEvent,
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, Message, Status, streamChat } from "../lib/api";

interface Props {
  conversationId: number | null;
  status: Status | null;
  onConversationCreated: (id: number) => void;
  onTitleMaybeChanged: () => void;
}

export default function ChatView({
  conversationId,
  status,
  onConversationCreated,
  onTitleMaybeChanged,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [images, setImages] = useState<string[]>([]); // base64, no prefix
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (conversationId != null) {
      api.messages(conversationId).then(setMessages);
    } else {
      setMessages([]);
    }
  }, [conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addImageFiles = (files: FileList | File[]) => {
    for (const file of Array.from(files)) {
      if (!file.type.startsWith("image/")) continue;
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = String(reader.result).split(",")[1];
        if (base64) setImages((prev) => [...prev, base64]);
      };
      reader.readAsDataURL(file);
    }
  };

  const onPaste = (e: ClipboardEvent) => {
    const files = Array.from(e.clipboardData.files);
    if (files.length > 0) {
      e.preventDefault();
      addImageFiles(files); // screenshots pasted straight from clipboard
    }
  };

  const send = async () => {
    const text = input.trim();
    if ((!text && images.length === 0) || busy) return;
    setError("");
    setBusy(true);
    setInput("");
    const sentImages = images;
    setImages([]);

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text, images: sentImages },
      { role: "assistant", content: "", images: [] },
    ]);

    const patchLast = (patch: (m: Message) => Message) =>
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = patch(next[next.length - 1]);
        return next;
      });

    try {
      await streamChat(
        { conversation_id: conversationId, message: text, images: sentImages },
        (event) => {
          if (event.type === "conversation" && conversationId == null) {
            onConversationCreated(event.id);
          } else if (event.type === "meta" && event.skills.length > 0) {
            patchLast((m) => ({ ...m, skills: event.skills }));
          } else if (event.type === "token") {
            patchLast((m) => ({ ...m, content: m.content + event.content }));
          } else if (event.type === "memory") {
            const notes = [
              ...event.remembered.map((r) => `Remembered: ${r.content}`),
              ...event.forgotten.map((f) => `Forgot: ${f.content}`),
            ];
            patchLast((m) => ({ ...m, memoryNote: notes.join(" · ") }));
          } else if (event.type === "error") {
            patchLast((m) => ({ ...m, error: event.message }));
          }
        },
      );
    } catch (err) {
      setMessages((prev) => prev.slice(0, -1));
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
      onTitleMaybeChanged();
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const offline = !status?.reachable || !status?.model;
  // Warn when images are attached but neither the main model reports vision
  // capability nor a dedicated vision model is configured.
  const noVision =
    images.length > 0 &&
    !!status?.reachable &&
    !!status?.model &&
    !status.vision_model &&
    !status.capabilities.includes("vision");

  return (
    <div className="chat">
      <div className="chat-scroll">
        {messages.length === 0 && (
          <div className="chat-empty">
            <h1>How can I help?</h1>
            <p>
              Ask anything, attach an image or paste a screenshot. I remember
              what matters across conversations, and skills activate
              automatically when relevant.
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.skills && m.skills.length > 0 && (
              <div className="msg-skills">
                {m.skills.map((s) => (
                  <span key={s} className="chip">
                    {s}
                  </span>
                ))}
              </div>
            )}
            {m.images.length > 0 && (
              <div className="msg-images">
                {m.images.map((img, j) => (
                  <img key={j} src={`data:image/png;base64,${img}`} alt="" />
                ))}
              </div>
            )}
            <div className="msg-body">
              {m.role === "assistant" ? (
                m.content ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {m.content}
                  </ReactMarkdown>
                ) : (
                  !m.error && <span className="thinking">Thinking…</span>
                )
              ) : (
                m.content
              )}
            </div>
            {m.error && <div className="msg-error">{m.error}</div>}
            {m.memoryNote && <div className="msg-memory">{m.memoryNote}</div>}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="composer-wrap">
        {error && <div className="banner error">{error}</div>}
        {offline && (
          <div className="banner warn">
            {status?.reachable
              ? "No model selected — choose one in Settings."
              : "Model endpoint unreachable — check Settings."}
          </div>
        )}
        {noVision && (
          <div className="banner warn">
            {status?.model} doesn't report vision support — the image will
            likely be ignored. Set a vision model in Settings (e.g.{" "}
            <code>moondream</code>) to handle image turns.
          </div>
        )}
        {images.length > 0 && (
          <div className="attachments">
            {images.map((img, i) => (
              <div key={i} className="attachment">
                <img src={`data:image/png;base64,${img}`} alt="" />
                <button
                  className="icon-btn"
                  onClick={() =>
                    setImages((prev) => prev.filter((_, j) => j !== i))
                  }
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="composer">
          <button
            className="icon-btn attach"
            title="Attach image"
            onClick={() => fileRef.current?.click()}
          >
            +
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            multiple
            hidden
            onChange={(e) => {
              if (e.target.files) addImageFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <textarea
            value={input}
            placeholder="Message the assistant… (paste a screenshot directly)"
            rows={1}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            onPaste={onPaste}
          />
          <button
            className="btn primary send"
            disabled={busy || (!input.trim() && images.length === 0)}
            onClick={send}
          >
            {busy ? "…" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
