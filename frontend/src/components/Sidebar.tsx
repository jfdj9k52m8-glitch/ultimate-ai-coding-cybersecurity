import { Conversation, Status } from "../lib/api";
import { View } from "../App";

interface Props {
  view: View;
  setView: (view: View) => void;
  conversations: Conversation[];
  activeId: number | null;
  status: Status | null;
  onSelect: (id: number) => void;
  onNewChat: () => void;
  onDelete: (id: number) => void;
}

export default function Sidebar({
  view,
  setView,
  conversations,
  activeId,
  status,
  onSelect,
  onNewChat,
  onDelete,
}: Props) {
  const online = Boolean(status?.reachable && status?.model);
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className={`status-dot ${online ? "on" : "off"}`} />
        <div>
          <div className="brand-name">Assistant</div>
          <div className="brand-sub">
            {online
              ? status?.model
              : status?.reachable
                ? "no model selected"
                : "model offline"}
          </div>
        </div>
      </div>

      <button className="btn primary new-chat" onClick={onNewChat}>
        + New chat
      </button>

      <div className="conv-list">
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`conv-item ${view === "chat" && c.id === activeId ? "active" : ""}`}
            onClick={() => onSelect(c.id)}
          >
            <span className="conv-title">{c.title}</span>
            <button
              className="icon-btn conv-delete"
              title="Delete conversation"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(c.id);
              }}
            >
              ×
            </button>
          </div>
        ))}
        {conversations.length === 0 && (
          <div className="conv-empty">No conversations yet</div>
        )}
      </div>

      <nav className="side-nav">
        {(
          [
            ["memory", "Memory"],
            ["skills", "Skills"],
            ["settings", "Settings"],
          ] as [View, string][]
        ).map(([id, label]) => (
          <button
            key={id}
            className={`nav-item ${view === id ? "active" : ""}`}
            onClick={() => setView(id)}
          >
            {label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
