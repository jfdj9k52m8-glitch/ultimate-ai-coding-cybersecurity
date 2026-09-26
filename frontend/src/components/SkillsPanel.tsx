import { useEffect, useState } from "react";
import { api, Skill } from "../lib/api";

export default function SkillsPanel() {
  const [skills, setSkills] = useState<Skill[]>([]);

  const refresh = () => api.skills().then(setSkills);
  useEffect(() => {
    refresh();
  }, []);

  const toggle = async (skill: Skill) => {
    await api.toggleSkill(skill.id, !skill.enabled);
    refresh();
  };

  return (
    <div className="panel">
      <header className="panel-head">
        <h1>Skills</h1>
        <p>
          Modular capabilities that activate automatically when a message
          matches them. Each skill is a self-contained pack in{" "}
          <code>backend/skills/</code> — drop in a folder to add one.
        </p>
      </header>

      <div className="skill-list">
        {skills.map((s) => (
          <div key={s.id} className={`skill-card ${s.enabled ? "" : "off"}`}>
            <div className="skill-info">
              <div className="skill-name">{s.name}</div>
              <div className="skill-desc">{s.description}</div>
              <div className="skill-keywords">
                {s.keywords.slice(0, 8).map((k) => (
                  <span key={k} className="chip">
                    {k}
                  </span>
                ))}
                {s.keywords.length > 8 && (
                  <span className="chip">+{s.keywords.length - 8} more</span>
                )}
              </div>
            </div>
            <label className="switch">
              <input
                type="checkbox"
                checked={s.enabled}
                onChange={() => toggle(s)}
              />
              <span className="slider" />
            </label>
          </div>
        ))}
        {skills.length === 0 && (
          <div className="panel-empty">No skill packs found.</div>
        )}
      </div>
    </div>
  );
}
