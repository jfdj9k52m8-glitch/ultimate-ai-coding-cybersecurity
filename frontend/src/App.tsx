import { useCallback, useEffect, useState } from "react";
import { api, Conversation, Status } from "./lib/api";
import Sidebar from "./components/Sidebar";
import ChatView from "./components/ChatView";
import MemoryPanel from "./components/MemoryPanel";
import SkillsPanel from "./components/SkillsPanel";
import SettingsPanel from "./components/SettingsPanel";

export type View = "chat" | "memory" | "skills" | "settings";

export default function App() {
  const [view, setView] = useState<View>("chat");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [status, setStatus] = useState<Status | null>(null);

  const refreshConversations = useCallback(async () => {
    setConversations(await api.conversations());
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      setStatus(await api.status());
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    refreshConversations();
    refreshStatus();
    const timer = setInterval(refreshStatus, 15000);
    return () => clearInterval(timer);
  }, [refreshConversations, refreshStatus]);

  const newChat = () => {
    setActiveId(null);
    setView("chat");
  };

  const deleteConversation = async (id: number) => {
    await api.deleteConversation(id);
    if (id === activeId) setActiveId(null);
    refreshConversations();
  };

  return (
    <div className="app">
      <Sidebar
        view={view}
        setView={setView}
        conversations={conversations}
        activeId={activeId}
        status={status}
        onSelect={(id) => {
          setActiveId(id);
          setView("chat");
        }}
        onNewChat={newChat}
        onDelete={deleteConversation}
      />
      <main className="main">
        {view === "chat" && (
          <ChatView
            key={activeId ?? "new"}
            conversationId={activeId}
            status={status}
            onConversationCreated={(id) => {
              setActiveId(id);
              refreshConversations();
            }}
            onTitleMaybeChanged={refreshConversations}
          />
        )}
        {view === "memory" && <MemoryPanel />}
        {view === "skills" && <SkillsPanel />}
        {view === "settings" && <SettingsPanel onSaved={refreshStatus} />}
      </main>
    </div>
  );
}
