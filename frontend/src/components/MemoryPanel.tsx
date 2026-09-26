import { FormEvent, useEffect, useState } from "react";
import { api, Memory } from "../lib/api";

const CATEGORIES = ["preference", "fact", "project", "task", "other"];

export default function MemoryPanel() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("fact");

  const refresh = () => api.memories().then(setMemories);
  useEffect(() => {
    refresh();
  }, []);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    await api.addMemory(content.trim(), category);
    setContent("");
    refresh();
  };

  const forget = async (id: number) => {
    await api.deleteMemory(id);
    refresh();
  };

  return (
    <div className="panel">
      <header className="panel-head">
        <h1>Memory</h1>
        <p>
          What the assistant remembers about you across conversations. It also
          learns automatically as you chat — and forgets when you ask it to.
        </p>
      </header>

      <form className="memory-add" onSubmit={add}>
        <input
          value={content}
          placeholder="Add something to remember…"
          onChange={(e) => setContent(e.target.value)}
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <button className="btn primary" type="submit">
          Remember
        </button>
      </form>

      <div className="memory-list">
        {memories.map((m) => (
          <div key={m.id} className="memory-item">
            <span className={`chip cat-${m.category}`}>{m.category}</span>
            <span className="memory-content">{m.content}</span>
            <button
              className="icon-btn"
              title="Forget"
              onClick={() => forget(m.id)}
            >
              ×
            </button>
          </div>
        ))}
        {memories.length === 0 && (
          <div className="panel-empty">
            Nothing remembered yet. Tell the assistant about yourself, your
            preferences or your projects — or add a memory manually above.
          </div>
        )}
      </div>
    </div>
  );
}
