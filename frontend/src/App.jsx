import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  ExternalLink,
  Bot,
  User,
  AlertCircle,
  Menu,
  X,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  FileText,
  Code,
  Copy,
  Download,
  RefreshCw,
  ArrowUp,
  PanelLeftClose,
  PanelLeftOpen
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

function generateSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

const SAMPLE_PROMPTS = [
  'How can I improve product retention?',
  "What does Patrick Campbell say about cancellation flows?",
  'Explain Lenny\'s growth frameworks',
  'Create a retention strategy'
];

// Helper to format inline markdown bold text (**text**)
function renderInline(str) {
  if (!str) return null;
  const parts = str.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={idx} className="font-semibold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

// Formatted text component to render paragraphs, lists, and bold text without raw markdown symbols
function FormattedText({ text }) {
  if (!text) return null;

  const blocks = text.split(/\n\n+/);

  return (
    <div className="space-y-3 text-slate-800 leading-relaxed text-sm">
      {blocks.map((block, bIdx) => {
        const trimmed = block.trim();
        const lines = trimmed.split('\n');
        const isBulletList = lines.length > 1 && lines.every((l) => /^\s*[\*\-•]\s+/.test(l));
        const isNumberedList = lines.length > 1 && lines.every((l) => /^\s*\d+\.\s+/.test(l));

        if (isBulletList) {
          return (
            <ul key={bIdx} className="list-disc pl-5 space-y-1.5 my-2 text-slate-800">
              {lines.map((line, lIdx) => {
                const content = line.replace(/^\s*[\*\-•]\s+/, '');
                return <li key={lIdx}>{renderInline(content)}</li>;
              })}
            </ul>
          );
        }

        if (isNumberedList) {
          return (
            <ol key={bIdx} className="list-decimal pl-5 space-y-1.5 my-2 text-slate-800">
              {lines.map((line, lIdx) => {
                const content = line.replace(/^\s*\d+\.\s+/, '');
                return <li key={lIdx}>{renderInline(content)}</li>;
              })}
            </ol>
          );
        }

        return (
          <p key={bIdx}>
            {lines.map((line, lIdx) => (
              <React.Fragment key={lIdx}>
                {renderInline(line)}
                {lIdx < lines.length - 1 && <br />}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}

export default function App() {
  const [sessionId, setSessionId] = useState(() => generateSessionId());
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem('lenny_chat_sessions');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // Configurable LLM Provider
  const [llmProvider, setLlmProvider] = useState('ollama');

  // Artifact State
  const [artifact, setArtifact] = useState(null);
  const [isGeneratingArtifact, setIsGeneratingArtifact] = useState(false);
  const [artifactFormat, setArtifactFormat] = useState('markdown');
  const [artifactError, setArtifactError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [lastArtifactPrompt, setLastArtifactPrompt] = useState('');

  // Sources Accordion State (Expanded message IDs)
  const [expandedSources, setExpandedSources] = useState({});

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Save sessions list to local storage
  useEffect(() => {
    try {
      localStorage.setItem('lenny_chat_sessions', JSON.stringify(sessions));
    } catch (e) {
      console.error('Failed to save sessions:', e);
    }
  }, [sessions]);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, isGeneratingArtifact]);

  // Auto-resize input textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  const toggleSourceExpand = (msgId) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  // Start new chat session
  const handleNewChat = () => {
    if (messages.length > 0) {
      const firstUserMsg = messages.find((m) => m.sender === 'user');
      const title = firstUserMsg ? firstUserMsg.text.slice(0, 32) + '...' : 'New Chat';

      const updatedSessions = [
        {
          id: sessionId,
          title,
          createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          messageCount: messages.length,
          messages: messages
        },
        ...sessions.filter((s) => s.id !== sessionId)
      ];
      setSessions(updatedSessions);
    }

    const newId = generateSessionId();
    setSessionId(newId);
    setMessages([]);
    setError(null);
    setArtifact(null);
    setArtifactError(null);
    setInput('');
    setMobileDrawerOpen(false);
  };

  // Switch to an existing session
  const handleSelectSession = (session) => {
    if (session.id === sessionId) return;

    if (messages.length > 0) {
      const firstUserMsg = messages.find((m) => m.sender === 'user');
      const title = firstUserMsg ? firstUserMsg.text.slice(0, 32) + '...' : 'Chat Session';
      setSessions((prev) => [
        {
          id: sessionId,
          title,
          createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          messageCount: messages.length,
          messages: messages
        },
        ...prev.filter((s) => s.id !== sessionId && s.id !== session.id)
      ]);
    }

    setSessionId(session.id);
    setMessages(session.messages || []);
    setError(null);
    setArtifact(null);
    setArtifactError(null);
    setMobileDrawerOpen(false);
  };

  // Send message to API
  const handleSendMessage = async (textToSend = input) => {
    const trimmed = textToSend.trim();
    if (!trimmed || isLoading) return;

    setError(null);
    const userMsgId = Date.now().toString();
    const userMessage = {
      id: userMsgId,
      sender: 'user',
      text: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: trimmed,
          provider: llmProvider
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const data = await response.json();
      const assistantMsgId = (Date.now() + 1).toString();

      const assistantMessage = {
        id: assistantMsgId,
        sender: 'assistant',
        text: data.message || 'No response received from model.',
        sources: data.sources || [],
        provider: data.provider || llmProvider,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      // Expand sources by default if present
      if (data.sources && data.sources.length > 0) {
        setExpandedSources((prev) => ({ ...prev, [assistantMsgId]: true }));
      }

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error('API Error:', err);
      setError('Please check that the backend is running and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Generate Artifact API Call
  const handleGenerateArtifact = async (promptText = input || 'Create product retention strategy', format = artifactFormat) => {
    const trimmedPrompt = promptText.trim();
    if (!trimmedPrompt || isGeneratingArtifact) return;

    setArtifactError(null);
    setLastArtifactPrompt(trimmedPrompt);
    setIsGeneratingArtifact(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/artifacts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          prompt: trimmedPrompt,
          format: format,
          provider: llmProvider
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Artifact server error: ${response.status}`);
      }

      const data = await response.json();
      setArtifact(data);

      const systemNotice = {
        id: Date.now().toString(),
        sender: 'assistant',
        text: `✨ **Generated ${data.format.toUpperCase()} Artifact**: "${data.title}"\n\nThe artifact is ready in the Artifact Workspace panel on the right.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages((prev) => [...prev, systemNotice]);
    } catch (err) {
      console.error('Artifact Error:', err);
      setArtifactError(err.message || 'Failed to generate artifact.');
    } finally {
      setIsGeneratingArtifact(false);
    }
  };

  const handleCopyArtifact = () => {
    if (!artifact?.content) return;
    navigator.clipboard.writeText(artifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadArtifact = () => {
    if (!artifact?.content) return;
    const extension = artifact.format === 'html' ? 'html' : 'md';
    const mimeType = artifact.format === 'html' ? 'text/html' : 'text/markdown';
    const safeTitle = (artifact.title || 'artifact').toLowerCase().replace(/[^a-z0-9]/g, '_');
    
    const blob = new Blob([artifact.content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safeTitle}.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Reusable Sidebar Component Content
  const SidebarContent = () => (
    <div className="flex flex-col h-full bg-slate-50 border-r border-slate-200/80 text-slate-800">
      {/* Sidebar Top / Branding */}
      <div className="p-4 border-b border-slate-200/80 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-violet-600 text-white font-bold flex items-center justify-center text-sm shadow-sm">
            L
          </div>
          <div>
            <h1 className="font-semibold text-slate-900 text-sm tracking-tight leading-none">
              Lenny Growth Assistant
            </h1>
            <p className="text-[11px] text-violet-600 font-medium mt-1">AI Product & Growth</p>
          </div>
        </div>
        {mobileDrawerOpen && (
          <button
            onClick={() => setMobileDrawerOpen(false)}
            className="lg:hidden text-slate-400 hover:text-slate-600 p-1 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 bg-violet-600 hover:bg-violet-700 active:bg-violet-800 text-white font-medium py-2.5 px-4 rounded-xl shadow-xs transition-all duration-150 text-xs cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Recent Conversations List */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        <div className="px-3 py-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Recent conversations
        </div>

        {sessions.length === 0 ? (
          <div className="px-3 py-8 text-center text-xs text-slate-400 font-normal">
            No previous conversations
          </div>
        ) : (
          sessions.map((s) => {
            const isActive = s.id === sessionId;
            return (
              <button
                key={s.id}
                onClick={() => handleSelectSession(s)}
                className={`w-full text-left px-3 py-2.5 rounded-xl text-xs flex items-center justify-between group transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-violet-100/70 text-violet-950 font-medium border border-violet-200/80 shadow-2xs'
                    : 'text-slate-600 hover:bg-slate-200/60 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0 pr-2">
                  <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-violet-600' : 'text-slate-400 group-hover:text-slate-600'}`} />
                  <span className="truncate">{s.title || 'Chat Session'}</span>
                </div>
                <span className="text-[10px] text-slate-400 shrink-0">{s.createdAt}</span>
              </button>
            );
          })
        )}
      </div>

      {/* Sidebar Bottom / Info & Settings */}
      <div className="p-3 border-t border-slate-200/80 bg-slate-100/50 text-[11px] text-slate-500 flex items-center justify-between">
        <span className="truncate">Ollama · Local Engine</span>
        <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" title="Connected" />
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 font-sans overflow-hidden">
      {/* Mobile Drawer Overlay */}
      {mobileDrawerOpen && (
        <div
          className="fixed inset-0 bg-slate-900/40 z-40 lg:hidden backdrop-blur-xs transition-opacity"
          onClick={() => setMobileDrawerOpen(false)}
        />
      )}

      {/* Mobile Sidebar Drawer */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-72 transition-transform duration-200 ease-in-out lg:hidden ${
          mobileDrawerOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <SidebarContent />
      </div>

      {/* Desktop Collapsible Sidebar */}
      {sidebarOpen && (
        <aside className="hidden lg:block w-72 shrink-0 h-full">
          <SidebarContent />
        </aside>
      )}

      {/* Main Workspace (Chat + Optional Artifact Workspace) */}
      <div className="flex-1 flex h-full overflow-hidden min-w-0">
        {/* Main Chat App Shell */}
        <main className={`flex flex-col h-full relative overflow-hidden bg-white transition-all duration-200 ${
          artifact ? 'w-full lg:w-1/2 border-r border-slate-200' : 'w-full'
        }`}>
          {/* Main Top Header */}
          <header className="h-14 border-b border-slate-200/80 bg-white/80 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between z-10 shrink-0">
            <div className="flex items-center gap-3">
              {/* Sidebar toggle button */}
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="hidden lg:flex text-slate-500 hover:text-slate-800 p-1.5 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
              >
                {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
              </button>

              <button
                onClick={() => setMobileDrawerOpen(true)}
                className="lg:hidden text-slate-500 hover:text-slate-800 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <Menu className="w-5 h-5" />
              </button>

              <div>
                <h2 className="font-semibold text-slate-900 text-sm tracking-tight leading-tight">
                  Lenny Growth Assistant
                </h2>
                <p className="text-[11px] text-violet-600 font-medium hidden sm:block">
                  AI-powered product & growth assistant
                </p>
              </div>
            </div>

            {/* Configurable Provider Selector */}
            <div className="flex items-center gap-2 bg-slate-100 border border-slate-200 rounded-full px-3 py-1 text-xs shrink-0 shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <select
                value={llmProvider}
                onChange={(e) => setLlmProvider(e.target.value)}
                className="bg-transparent text-slate-700 font-medium text-xs focus:outline-none cursor-pointer"
              >
                <option value="ollama">Ollama · Local</option>
                <option value="openai">OpenAI · GPT-4o</option>
                <option value="anthropic">Anthropic · Claude 3.5</option>
              </select>
            </div>
          </header>

          {/* Chat Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
            {messages.length === 0 ? (
              /* ChatGPT-style Empty Welcome State */
              <div className="max-w-2xl mx-auto my-auto py-12 px-4 text-center space-y-6">
                <div className="w-14 h-14 rounded-full bg-violet-100 border border-violet-200 text-violet-600 font-bold text-xl flex items-center justify-center mx-auto shadow-xs">
                  L
                </div>
                <div className="space-y-1.5">
                  <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
                    Lenny Growth Assistant
                  </h2>
                  <p className="text-sm text-slate-500 max-w-md mx-auto">
                    Your AI partner for product, growth, and Lenny's knowledge.
                  </p>
                </div>

                {/* 4 Suggested Prompts Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left pt-3">
                  {SAMPLE_PROMPTS.map((promptText, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(promptText)}
                      className="p-4 rounded-2xl bg-white hover:bg-violet-50/40 border border-slate-200 hover:border-violet-300 shadow-2xs hover:shadow-sm text-xs text-slate-700 font-medium transition-all duration-200 group flex items-start justify-between cursor-pointer"
                    >
                      <span className="leading-relaxed group-hover:text-slate-900">{promptText}</span>
                      <Sparkles className="w-4 h-4 text-violet-500 shrink-0 ml-2 group-hover:translate-x-0.5 transition-transform" />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* Chat Message Stream */
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 max-w-3xl ${
                    msg.sender === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
                  }`}
                >
                  {/* User or Assistant Avatar */}
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs font-bold shadow-2xs ${
                      msg.sender === 'user'
                        ? 'bg-slate-700 text-white'
                        : 'bg-violet-600 text-white'
                    }`}
                  >
                    {msg.sender === 'user' ? 'U' : 'L'}
                  </div>

                  {/* Message Bubble Container */}
                  <div className="space-y-2.5 min-w-0 max-w-[88%]">
                    <div
                      className={`rounded-2xl p-4 text-sm leading-relaxed ${
                        msg.sender === 'user'
                          ? 'bg-violet-100/80 border border-violet-200/80 text-slate-900 rounded-tr-xs shadow-2xs'
                          : 'bg-white border border-slate-200/80 text-slate-800 rounded-tl-xs shadow-2xs'
                      }`}
                    >
                      {msg.sender === 'user' ? (
                        <div className="whitespace-pre-wrap text-slate-900 font-normal">{msg.text}</div>
                      ) : (
                        <FormattedText text={msg.text} />
                      )}

                      <div className="text-[10px] mt-2 flex items-center justify-between text-slate-400">
                        {msg.sender === 'assistant' && (
                          <button
                            onClick={() => handleGenerateArtifact(msg.text, 'markdown')}
                            disabled={isGeneratingArtifact}
                            className="inline-flex items-center gap-1.5 text-xs text-violet-700 hover:text-violet-900 font-medium bg-violet-50 hover:bg-violet-100 border border-violet-200 px-2.5 py-1 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                          >
                            <Sparkles className="w-3.5 h-3.5 text-violet-600" />
                            <span>Create Artifact</span>
                          </button>
                        )}
                        <span className="ml-auto">{msg.timestamp}</span>
                      </div>
                    </div>

                    {/* Collapsible Sources Section */}
                    {msg.sender === 'assistant' && msg.sources && msg.sources.length > 0 && (
                      <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-3 space-y-2 text-xs">
                        <button
                          onClick={() => toggleSourceExpand(msg.id)}
                          className="w-full flex items-center justify-between text-slate-600 font-medium hover:text-slate-900 cursor-pointer"
                        >
                          <div className="flex items-center gap-1.5 text-violet-700 font-semibold">
                            <BookOpen className="w-3.5 h-3.5" />
                            <span>Sources · {msg.sources.length}</span>
                          </div>
                          {expandedSources[msg.id] ? (
                            <ChevronUp className="w-4 h-4 text-slate-400" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-slate-400" />
                          )}
                        </button>

                        {expandedSources[msg.id] && (
                          <div className="grid grid-cols-1 gap-2 pt-1 border-t border-slate-200/80">
                            {msg.sources.map((src, index) => (
                              <div
                                key={index}
                                className="p-2.5 rounded-lg bg-white border border-slate-200/80 hover:border-slate-300 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                              >
                                <div className="space-y-0.5 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="font-semibold text-slate-900 truncate">
                                      {src.guest || 'Lenny Expert'}
                                    </span>
                                    <span className="text-[10px] bg-violet-100 text-violet-700 font-mono px-1.5 py-0.2 rounded font-medium">
                                      Chunk #{src.chunk_index ?? index + 1}
                                    </span>
                                  </div>
                                  <p className="text-slate-500 text-[11px] truncate">
                                    {src.title || 'Lenny Podcast Transcript'}
                                  </p>
                                </div>

                                {src.url && (
                                  <a
                                    href={src.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 text-violet-600 hover:text-violet-800 text-[11px] font-medium shrink-0"
                                  >
                                    <span>Watch Episode</span>
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {/* Minimal "Thinking..." Loading Indicator */}
            {isLoading && (
              <div className="flex gap-3 max-w-3xl mr-auto animate-fade-in">
                <div className="w-7 h-7 rounded-full bg-violet-600 text-white font-bold flex items-center justify-center text-xs shrink-0 shadow-2xs">
                  L
                </div>
                <div className="bg-white border border-slate-200/80 rounded-2xl rounded-tl-xs p-3.5 flex items-center gap-2.5 shadow-2xs">
                  <span className="w-2 h-2 rounded-full bg-violet-600 animate-ping" />
                  <span className="text-xs text-slate-600 font-medium">Thinking...</span>
                </div>
              </div>
            )}

            {/* Artifact Generation Loading Banner */}
            {isGeneratingArtifact && (
              <div className="p-3.5 rounded-xl bg-violet-50 border border-violet-200 text-violet-900 text-xs flex items-center gap-3 max-w-xl mx-auto animate-pulse">
                <Sparkles className="w-4 h-4 text-violet-600 animate-spin" />
                <div>
                  <p className="font-semibold">Generating Grounded Artifact ({artifactFormat.toUpperCase()})...</p>
                  <p className="text-violet-700/80 text-[11px]">Synthesizing document from retrieved transcripts...</p>
                </div>
              </div>
            )}

            {/* Polished Inline Error Alert */}
            {error && (
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-start gap-3 max-w-xl mx-auto">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <div className="flex-1 space-y-1">
                  <p className="font-semibold text-rose-950">Something went wrong</p>
                  <p className="text-rose-800 leading-relaxed">{error}</p>
                </div>
                <button
                  onClick={() => handleSendMessage()}
                  className="px-2.5 py-1 bg-white hover:bg-rose-100 border border-rose-300 text-rose-900 rounded-lg font-medium text-[11px] shrink-0 transition-colors"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Artifact Error Alert */}
            {artifactError && (
              <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between gap-3 max-w-xl mx-auto">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>Artifact Error: {artifactError}</span>
                </div>
                <button
                  onClick={() => handleGenerateArtifact(lastArtifactPrompt || 'Create retention guide')}
                  className="px-2.5 py-1 bg-white hover:bg-amber-100 border border-amber-300 text-amber-900 rounded-lg text-[11px] font-medium shrink-0 transition-colors"
                >
                  Retry
                </button>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* ChatGPT-style Bottom Composer */}
          <div className="p-4 border-t border-slate-200/80 bg-white shrink-0 space-y-2">
            {/* Artifact Controls Bar */}
            <div className="flex items-center justify-between max-w-3xl mx-auto px-1 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-slate-500 font-medium text-[11px]">Format:</span>
                <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-[11px]">
                  <button
                    onClick={() => setArtifactFormat('markdown')}
                    className={`px-2 py-0.5 rounded-md font-medium transition-colors cursor-pointer ${
                      artifactFormat === 'markdown'
                        ? 'bg-white text-slate-900 shadow-2xs'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    Markdown
                  </button>
                  <button
                    onClick={() => setArtifactFormat('html')}
                    className={`px-2 py-0.5 rounded-md font-medium transition-colors cursor-pointer ${
                      artifactFormat === 'html'
                        ? 'bg-white text-slate-900 shadow-2xs'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    HTML
                  </button>
                </div>
              </div>

              <button
                onClick={() => handleGenerateArtifact(input || 'Create product retention guide', artifactFormat)}
                disabled={isGeneratingArtifact}
                className="inline-flex items-center gap-1.5 text-xs text-violet-700 hover:text-violet-900 bg-violet-50 hover:bg-violet-100 border border-violet-200 px-3 py-1 rounded-lg font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5 text-violet-600" />
                <span>Create Artifact [{artifactFormat.toUpperCase()}]</span>
              </button>
            </div>

            {/* Rounded Input Box Container */}
            <div className="max-w-3xl mx-auto relative flex items-end bg-white rounded-2xl border border-slate-300 focus-within:border-violet-500 focus-within:ring-2 focus-within:ring-violet-500/20 shadow-xs transition-all p-2">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask Lenny anything..."
                rows={1}
                disabled={isLoading || isGeneratingArtifact}
                className="flex-1 bg-transparent border-0 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-0 resize-none max-h-44 py-2 px-2"
              />
              <button
                onClick={() => handleSendMessage()}
                disabled={isLoading || isGeneratingArtifact || !input.trim()}
                className="ml-2 w-8 h-8 rounded-xl bg-violet-600 hover:bg-violet-700 disabled:bg-slate-200 text-white disabled:text-slate-400 flex items-center justify-center transition-all cursor-pointer shrink-0 shadow-xs"
                title="Send message"
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            </div>

            {/* Small Disclaimer */}
            <p className="text-[11px] text-slate-400 text-center">
              Lenny Growth Assistant can make mistakes. Check sources for important decisions.
            </p>
          </div>
        </main>

        {/* Right-Side Artifact Viewer Workspace Panel */}
        {artifact && (
          <aside className="w-full lg:w-1/2 h-full bg-white border-l border-slate-200 flex flex-col z-20 shadow-xl">
            {/* Artifact Header */}
            <div className="p-4 border-b border-slate-200 bg-slate-50/80 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3 min-w-0 pr-2">
                <div className="w-8 h-8 rounded-lg bg-violet-100 border border-violet-200 text-violet-600 flex items-center justify-center shrink-0 font-bold">
                  {artifact.format === 'html' ? <Code className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                </div>
                <div className="min-w-0">
                  <h3 className="font-semibold text-slate-900 text-sm truncate">{artifact.title || 'Generated Artifact'}</h3>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono font-bold uppercase bg-violet-100 text-violet-700 border border-violet-200 px-1.5 py-0.2 rounded">
                      {artifact.format}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">ID: {artifact.artifact_id}</span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={handleCopyArtifact}
                  className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs"
                >
                  {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-500" />}
                  <span>{copied ? 'Copied!' : 'Copy'}</span>
                </button>

                <button
                  onClick={handleDownloadArtifact}
                  className="px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </button>

                <button
                  onClick={() => setArtifact(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Artifact Body */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-slate-50">
              {artifact.format === 'html' ? (
                /* Secure Sandboxed iframe for HTML */
                <iframe
                  sandbox=""
                  srcDoc={artifact.content}
                  title={artifact.title}
                  className="w-full h-full min-h-[600px] border border-slate-200 rounded-xl bg-white shadow-xs"
                />
              ) : (
                /* Styled Markdown Content */
                <div className="bg-white border border-slate-200 rounded-2xl p-6 text-slate-800 text-sm leading-relaxed whitespace-pre-wrap font-sans shadow-xs">
                  {artifact.content}
                </div>
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
