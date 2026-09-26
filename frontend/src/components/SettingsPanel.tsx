import { useEffect, useState } from "react";
import { api, Settings, Status } from "../lib/api";

interface Props {
  onSaved: () => void;
}

export default function SettingsPanel({ onSaved }: Props) {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [saved, setSaved] = useState(false);

  const refresh = async () => {
    setSettings(await api.getSettings());
    try {
      setStatus(await api.status());
    } catch {
      setStatus(null);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  if (!settings) return <div className="panel" />;

  const save = async () => {
    await api.updateSettings(settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    await refresh();
    onSaved();
  };

  const set = (patch: Partial<Settings>) =>
    setSettings({ ...settings, ...patch });

  return (
    <div className="panel">
      <header className="panel-head">
        <h1>Settings</h1>
        <p>
          The assistant talks to any Ollama-compatible endpoint — a local
          Ollama install or your own hosted/fine-tuned model.
        </p>
      </header>

      <div className="form">
        <label>
          <span>Endpoint URL</span>
          <input
            value={settings.base_url}
            onChange={(e) => set({ base_url: e.target.value })}
            placeholder="http://127.0.0.1:11434"
          />
        </label>

        <label>
          <span>Model</span>
          {status?.available_models.length ? (
            <select
              value={settings.model}
              onChange={(e) => set({ model: e.target.value })}
            >
              <option value="">— select a model —</option>
              {status.available_models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={settings.model}
              onChange={(e) => set({ model: e.target.value })}
              placeholder="model name"
            />
          )}
        </label>

        <label>
          <span>Vision model (optional — leave empty if the main model is multimodal)</span>
          <input
            value={settings.vision_model}
            onChange={(e) => set({ vision_model: e.target.value })}
            placeholder=""
          />
        </label>

        <label>
          <span>Context window (tokens)</span>
          <input
            type="number"
            min={2048}
            value={settings.context_tokens}
            onChange={(e) => set({ context_tokens: Number(e.target.value) })}
          />
          {status && (
            <small>
              Model supports:{" "}
              {status.model_max_context
                ? status.model_max_context.toLocaleString()
                : "unknown"}{" "}
              · effective:{" "}
              {status.effective_context_tokens.toLocaleString()} tokens
            </small>
          )}
        </label>

        <label>
          <span>Temperature</span>
          <input
            type="number"
            step={0.1}
            min={0}
            max={2}
            value={settings.temperature}
            onChange={(e) => set({ temperature: Number(e.target.value) })}
          />
        </label>

        <label className="row">
          <input
            type="checkbox"
            checked={settings.memory_extraction}
            onChange={(e) => set({ memory_extraction: e.target.checked })}
          />
          <span>Automatic memory (learn & forget from conversation)</span>
        </label>

        <div className="form-actions">
          <button className="btn primary" onClick={save}>
            {saved ? "Saved ✓" : "Save"}
          </button>
          <span className={`status-inline ${status?.reachable ? "on" : "off"}`}>
            {status?.reachable
              ? `Connected · ${status.available_models.length} model(s) available`
              : `Not reachable${status?.detail ? ` — ${status.detail}` : ""}`}
          </span>
        </div>
      </div>
    </div>
  );
}
