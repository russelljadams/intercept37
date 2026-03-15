import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useWebSocket } from "../hooks/useWebSocket";
import { useAgentChat } from "../hooks/useAgentChat";
import ChatPanel from "./ChatPanel";

const navItems = [
  { to: "/", label: "Dashboard", icon: ">" },
  { to: "/traffic", label: "Traffic", icon: "#" },
  { to: "/repeater", label: "Repeater", icon: "~" },
  { to: "/scanner", label: "Scanner", icon: "!" },
];

const LOGO_ASCII = `
 ___ _  _ _____ ___ ___  ___ ___ ___ _____
|_ _| \\| |_   _| __| _ \\/ __| __| _ \\_   _|
 | || .\` | | | | _||   / (__| _||  _/ | |
|___|_|\\_| |_| |___|_|_\\\\___|___|_|   |_|
                                    :::37:::`;

export default function Layout() {
  const { connected } = useWebSocket();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const agentChat = useAgentChat();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-alien-black scanline-bg">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed md:static z-40 h-full w-56 flex-shrink-0 border-r border-alien-border bg-alien-dark flex flex-col transition-transform duration-200 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        {/* Logo */}
        <div className="p-4 border-b border-alien-border">
          <pre className="text-alien-green text-[5px] sm:text-[6px] leading-[6px] sm:leading-[7px] glow-text font-mono select-none">
            {LOGO_ASCII}
          </pre>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 mx-2 rounded text-sm transition-all duration-200 ${
                  isActive
                    ? "bg-alien-green/10 text-alien-green glow-border"
                    : "text-alien-text-dim hover:text-alien-green hover:bg-alien-green/5"
                }`
              }
            >
              <span className="text-alien-green font-bold w-4 text-center">{item.icon}</span>
              <span className="tracking-wider uppercase text-xs">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Bottom info */}
        <div className="p-4 border-t border-alien-border text-[10px] text-alien-text-dim">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-alien-green">$</span>
            <span>v0.1.0-alpha</span>
          </div>
          <div className="text-alien-green/40">ALIEN INTERCEPTOR</div>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Top bar */}
        <header className="h-10 flex-shrink-0 border-b border-alien-border bg-alien-dark flex items-center justify-between px-3 sm:px-4">
          <div className="flex items-center gap-3">
            {/* Hamburger for mobile */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="md:hidden text-alien-green text-lg leading-none"
            >
              &#9776;
            </button>
            <span className="text-alien-text-dim text-[10px] sm:text-xs tracking-widest uppercase">
              Proxy Interface
            </span>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <div className="flex items-center gap-1.5 text-[10px] sm:text-xs">
              <div
                className={`w-2 h-2 rounded-full ${
                  connected
                    ? "bg-alien-green shadow-alien animate-glow-pulse"
                    : "bg-alien-red shadow-red"
                }`}
              />
              <span className={connected ? "text-alien-green" : "text-alien-red"}>
                {connected ? "LIVE" : "OFF"}
              </span>
            </div>
            <span className="text-alien-text-dim text-[10px] hidden sm:inline">
              localhost:1337
            </span>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-2 sm:p-4 grid-bg">
          <Outlet />
        </main>
      </div>

      {/* Floating Agent Button */}
      <button
        onClick={() => setChatOpen(!chatOpen)}
        className={`fixed bottom-4 right-4 z-20 w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-alien-green/20 border border-alien-green/50 text-alien-green hover:bg-alien-green/30 hover:shadow-alien flex items-center justify-center text-xl sm:text-2xl font-bold transition-all duration-200 ${
          !chatOpen ? "animate-glow-pulse" : ""
        }`}
        aria-label="Toggle Agent chat"
      >
        @
      </button>

      {/* Chat Panel */}
      <ChatPanel
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
        messages={agentChat.messages}
        isStreaming={agentChat.isStreaming}
        sendMessage={agentChat.sendMessage}
        clearSession={agentChat.clearSession}
      />
    </div>
  );
}
