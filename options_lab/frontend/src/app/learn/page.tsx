'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { optionsApi } from '@/lib/api';
import {
  BookOpen, Send, Sparkles, Loader, Save, Clock, Trash2,
  FolderOpen, PlusCircle, Check, ChevronRight, ChevronDown, X
} from 'lucide-react';
import ProtectedRoute from '@/components/ProtectedRoute';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface SessionMeta {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  key_learnings?: string;
}

type PanelView = 'chat' | 'sessions';

export default function LearnPage() {
  // ── Chat State ─────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        "Hello! I am your Socratic Options & Markets Tutor. I act as your Senior Financial Analyst and Research Assistant. I'm here to help you explore corporate finance, risk exposure, earnings, capital allocation, and market strategy. What concepts or portfolio events are you analyzing today?"
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  // ── Concept Card State ─────────────────────────────────────────────────────
  const [selectedConcept, setSelectedConcept] = useState<string | null>(null);
  const [conceptExplanation, setConceptExplanation] = useState<string>('');
  const [loadingConcept, setLoadingConcept] = useState(false);

  // ── Session State ──────────────────────────────────────────────────────────
  const [panelView, setPanelView] = useState<PanelView>('chat');
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [expandedSessionId, setExpandedSessionId] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [sessionTitle, setSessionTitle] = useState('');

  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollChat = () => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(() => { scrollChat(); }, [messages]);

  // ── Fetch sessions list ────────────────────────────────────────────────────
  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = await optionsApi.listSessions();
      setSessions(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Failed to load sessions', e);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  // ── Send message ───────────────────────────────────────────────────────────
  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput('');
    setLoading(true);

    try {
      const chatHistory = messages.map(m => ({ role: m.role, content: m.content }));
      const res = await optionsApi.askTutor({ message: text, chat_history: chatHistory });
      const newMessages = [...updatedMessages, { role: 'assistant' as const, content: res.response }];
      setMessages(newMessages);

      // Auto-save if there's an active session
      if (currentSessionId) {
        await optionsApi.updateSession(currentSessionId, newMessages);
        // Refresh sessions list to pull new key_learnings in background
        loadSessions();
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: "I had trouble connecting. Let's continue — what is your intuition about that?" }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend(input);
    }
  };

  // ── Concept Explanation ────────────────────────────────────────────────────
  const handleExplainConcept = async (concept: string) => {
    setSelectedConcept(concept);
    setLoadingConcept(true);
    try {
      const res = await optionsApi.explainConcept(concept);
      setConceptExplanation(res.explanation);
    } catch (err) {
      console.error(err);
      setConceptExplanation('Could not load the concept card at this moment.');
    } finally {
      setLoadingConcept(false);
    }
  };

  // ── Save Session ───────────────────────────────────────────────────────────
  const handleSaveSession = async () => {
    if (messages.length <= 1) return; // nothing to save beyond greeting
    const autoTitle = sessionTitle.trim() ||
      `Session — ${new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}`;

    setSaveStatus('saving');
    try {
      if (currentSessionId) {
        await optionsApi.updateSession(currentSessionId, messages, autoTitle);
      } else {
        const saved = await optionsApi.createSession(autoTitle, messages);
        setCurrentSessionId(saved.id);
      }
      setSaveStatus('saved');
      setShowSaveDialog(false);
      setSessionTitle('');
      loadSessions();
      setTimeout(() => setSaveStatus('idle'), 2500);
    } catch (e) {
      console.error(e);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  // ── Load Session ───────────────────────────────────────────────────────────
  const handleLoadSession = async (id: string) => {
    try {
      const data = await optionsApi.getSession(id);
      setMessages(data.messages);
      setCurrentSessionId(id);
      setPanelView('chat');
    } catch (e) {
      console.error('Failed to load session', e);
    }
  };

  // ── Delete Session ─────────────────────────────────────────────────────────
  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await optionsApi.deleteSession(id);
      if (currentSessionId === id) {
        setCurrentSessionId(null);
      }
      setSessions(prev => prev.filter(s => s.id !== id));
    } catch (e) {
      console.error('Failed to delete session', e);
    }
  };

  // ── New Chat ───────────────────────────────────────────────────────────────
  const handleNewChat = () => {
    setMessages([
      {
        role: 'assistant',
        content: "Hello again! Ready for a new learning journey. What would you like to explore?"
      }
    ]);
    setCurrentSessionId(null);
    setSaveStatus('idle');
    setPanelView('chat');
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString('en-GB', {
        day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
      });
    } catch { return iso; }
  };

  // ── Date grouping logic ───────────────────────────────────────────────────
  const getGroupedSessions = () => {
    const groups: Record<string, SessionMeta[]> = {
      'Today': [],
      'Yesterday': [],
      'Earlier this Week': [],
      'Older': []
    };

    const now = new Date();
    const todayStr = now.toLocaleDateString();
    
    const yesterday = new Date();
    yesterday.setDate(now.getDate() - 1);
    const yesterdayStr = yesterday.toLocaleDateString();

    const startOfWeek = new Date();
    startOfWeek.setDate(now.getDate() - now.getDay()); // Sunday

    sessions.forEach(session => {
      const date = new Date(session.updated_at);
      const dateStr = date.toLocaleDateString();

      if (dateStr === todayStr) {
        groups['Today'].push(session);
      } else if (dateStr === yesterdayStr) {
        groups['Yesterday'].push(session);
      } else if (date >= startOfWeek) {
        groups['Earlier this Week'].push(session);
      } else {
        groups['Older'].push(session);
      }
    });

    return Object.fromEntries(
      Object.entries(groups).filter(([_, items]) => items.length > 0)
    );
  };

  const quickPrompts = [
    "How do companies decide between stock buybacks and dividends?",
    "What is capital allocation and why does ROI matter?",
    "How does a tech firm hedge its key employee stock grant risk?",
    "What is the compounding mistake in the Legacy Monte Carlo code?"
  ];

  const conceptsList = [
    "Capital Allocation", "Risk Exposure", "Corporate Earnings",
    "Hedging Options", "Brownian Motion", "Option Greeks"
  ];

  const groupedSessions = getGroupedSessions();

  return (
    <ProtectedRoute>
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-[#5ba4b5]" /> Socratic Learning Tutor
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Deepen your understanding of financial markets, capital allocation, corporate earnings, and risk management through Socratic dialog.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {currentSessionId && (
            <span className="text-[10px] bg-[#5ba4b5]/10 text-[#5ba4b5] border border-[#5ba4b5]/30 rounded-full px-2.5 py-1">
              Session active
            </span>
          )}
          <button
            onClick={handleNewChat}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-600 transition"
          >
            <PlusCircle className="h-3.5 w-3.5" /> New Chat
          </button>
          <button
            onClick={() => { setPanelView(panelView === 'sessions' ? 'chat' : 'sessions'); loadSessions(); }}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition ${
              panelView === 'sessions'
                ? 'bg-[#5ba4b5]/10 border-[#5ba4b5] text-[#5ba4b5]'
                : 'border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-600'
            }`}
          >
            <Clock className="h-3.5 w-3.5" />
            Saved Sessions {sessions.length > 0 && <span className="ml-1 bg-[#5ba4b5]/20 text-[#5ba4b5] rounded-full px-1.5 text-[10px]">{sessions.length}</span>}
          </button>
        </div>
      </div>

      {/* ── Sessions Panel ─────────────────────────────────────────────────── */}
      {panelView === 'sessions' && (
        <div className="glass-card p-6 space-y-4 bg-[#161924]/80 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-slate-200 text-sm flex items-center gap-2">
              <FolderOpen className="h-4 w-4 text-[#5ba4b5]" /> Saved Learning Sessions
            </h2>
            <button onClick={() => setPanelView('chat')} className="text-slate-500 hover:text-slate-300 transition">
              <X className="h-4 w-4" />
            </button>
          </div>
          
          {sessionsLoading ? (
            <div className="flex items-center gap-2 text-xs text-slate-500 animate-pulse py-4">
              <Loader className="h-3 w-3 animate-spin" /> Loading sessions...
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-xs">
              <BookOpen className="h-8 w-8 mx-auto mb-2 opacity-30" />
              <p>No saved sessions yet.</p>
              <p className="mt-1 text-slate-600">Start a conversation and click <strong className="text-slate-400">Save Session</strong> to persist it.</p>
            </div>
          ) : (
            <div className="space-y-6">
              {Object.entries(groupedSessions).map(([groupName, groupItems]) => (
                <div key={groupName} className="space-y-2">
                  <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider border-b border-slate-800 pb-1">
                    {groupName}
                  </h3>
                  <div className="divide-y divide-slate-800/40">
                    {groupItems.map(session => (
                      <div key={session.id} className="py-2.5">
                        {/* Session Row */}
                        <div 
                          className={`flex items-center justify-between hover:bg-[#1a1d28]/40 rounded-lg px-3 py-2 transition group ${
                            currentSessionId === session.id ? 'bg-[#5ba4b5]/5 border-l-2 border-[#5ba4b5]' : ''
                          }`}
                        >
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            {/* Expand Key Learnings Button */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setExpandedSessionId(expandedSessionId === session.id ? null : session.id);
                              }}
                              className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition"
                              title="Toggle Key Learnings"
                            >
                              {expandedSessionId === session.id ? (
                                <ChevronDown className="h-4 w-4 text-[#5ba4b5]" />
                              ) : (
                                <ChevronRight className="h-4 w-4" />
                              )}
                            </button>
                            
                            {/* Clickable Title to Load Session */}
                            <div 
                              onClick={() => handleLoadSession(session.id)}
                              className="flex-1 cursor-pointer min-w-0"
                            >
                              <p className="text-xs text-slate-200 truncate font-semibold hover:text-[#5ba4b5] transition">
                                {session.title}
                              </p>
                              <p className="text-[9px] text-slate-500 mt-0.5 font-mono">
                                Updated: {formatDate(session.updated_at)}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 ml-3">
                            <button
                              onClick={() => handleLoadSession(session.id)}
                              className="text-[10px] text-slate-400 bg-slate-800/80 hover:bg-[#5ba4b5]/20 hover:text-[#5ba4b5] border border-slate-700 px-2 py-0.5 rounded transition"
                            >
                              Load Chat
                            </button>
                            <button
                              onClick={(e) => handleDeleteSession(session.id, e)}
                              className="p-1.5 rounded text-slate-600 hover:text-rose-400 hover:bg-rose-500/10 transition opacity-0 group-hover:opacity-100"
                              title="Delete Session"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </div>

                        {/* Collapsible Key Learnings Summary Block */}
                        {expandedSessionId === session.id && (
                          <div className="ml-10 mt-2 p-3.5 rounded-lg border border-[#5ba4b5]/20 bg-[#12141c]/60 space-y-2">
                            <span className="text-[9px] font-bold text-[#5ba4b5] uppercase tracking-wider block">
                              Key Financial Learnings
                            </span>
                            {session.key_learnings ? (
                              <ul className="list-disc list-inside space-y-1.5 text-slate-300 text-xs">
                                {session.key_learnings.split('\n').filter(line => line.trim().startsWith('-')).map((line, idx) => (
                                  <li key={idx} className="leading-relaxed pl-1">
                                    {line.replace(/^-\s*/, '')}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-slate-500 text-xs italic">No key learnings extracted. Chat longer to build a summary.</p>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Save Dialog ────────────────────────────────────────────────────── */}
      {showSaveDialog && (
        <div className="glass-card p-5 border border-[#5ba4b5]/30 space-y-3">
          <h3 className="text-sm font-bold text-slate-200">Save this Session</h3>
          <input
            type="text"
            value={sessionTitle}
            onChange={e => setSessionTitle(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSaveSession()}
            placeholder="Give this session a title (or leave blank for auto-title)..."
            autoFocus
            className="w-full rounded-lg px-4 py-2.5 text-xs"
          />
          <div className="flex gap-2">
            <button
              onClick={handleSaveSession}
              disabled={saveStatus === 'saving'}
              className="flex items-center gap-1.5 text-xs px-4 py-2 rounded-lg bg-[#5ba4b5] hover:bg-[#4a91a2] text-slate-900 font-semibold transition disabled:opacity-60"
            >
              {saveStatus === 'saving' ? <Loader className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
              {saveStatus === 'saving' ? 'Saving...' : 'Save'}
            </button>
            <button
              onClick={() => { setShowSaveDialog(false); setSessionTitle(''); }}
              className="text-xs px-3 py-2 rounded-lg border border-slate-700 text-slate-400 hover:text-slate-200 transition"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* ── Main Grid ─────────────────────────────────────────────────────── */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Chat Window */}
        <div className="lg:col-span-2 flex flex-col h-[600px] glass-card overflow-hidden">
          {/* Chat messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-3 max-w-[85%] ${
                  m.role === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
                }`}
              >
                <div className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                  m.role === 'user' ? 'bg-[#5ba4b5]/20 text-[#5ba4b5]' : 'bg-[#7ec8a0]/20 text-[#7ec8a0]'
                }`}>
                  {m.role === 'user' ? 'U' : 'AI'}
                </div>
                <div className={`p-4 rounded-xl text-sm leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-[#5ba4b5]/10 text-slate-200 rounded-tr-none'
                    : 'bg-[#1a1d28]/70 text-slate-300 rounded-tl-none border border-slate-800'
                }`}>
                  <div className="whitespace-pre-line prose prose-invert max-w-none text-xs">
                    {m.content}
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-3 mr-auto items-center text-xs text-slate-500 animate-pulse">
                <Loader className="h-4 w-4 animate-spin text-[#7ec8a0]" />
                Tutor is contemplating...
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Quick Prompts */}
          {messages.length === 1 && (
            <div className="px-6 py-3 border-t border-slate-800 bg-[#12141c]/30">
              <span className="text-[10px] text-slate-500 font-bold block mb-2 uppercase tracking-wider">
                Suggested Real-World Scenarios
              </span>
              <div className="grid gap-2">
                {quickPrompts.map(prompt => (
                  <button
                    key={prompt}
                    onClick={() => handleSend(prompt)}
                    className="text-left text-xs text-slate-400 hover:text-[#5ba4b5] hover:bg-[#1a1d28]/50 p-2 rounded transition border border-slate-800/40"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input Bar */}
          <div className="p-4 border-t border-slate-800 bg-[#161924]/60">
            <div className="flex items-center gap-2 mb-2">
              {/* Save Button */}
              {messages.length > 1 && (
                saveStatus === 'saved' ? (
                  <span className="flex items-center gap-1 text-[10px] text-[#7ec8a0]">
                    <Check className="h-3 w-3" /> Saved
                  </span>
                ) : (
                  <button
                    onClick={() => setShowSaveDialog(true)}
                    disabled={saveStatus === 'saving'}
                    className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-[#5ba4b5] transition"
                  >
                    <Save className="h-3 w-3" />
                    {currentSessionId ? 'Update Session' : 'Save Session'}
                  </button>
                )
              )}
            </div>
            <div className="flex gap-2 items-end">
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask your analyst tutor... (Ctrl+Enter to send)"
                rows={2}
                className="flex-1 rounded-lg px-4 py-2.5 text-xs bg-slate-900/60 text-slate-100 border border-slate-700/80 focus:outline-none focus:border-[#5ba4b5] transition min-h-[44px] max-h-[160px] overflow-y-auto resize-none"
              />
              <button
                onClick={() => handleSend(input)}
                disabled={loading}
                className="rounded-lg bg-[#5ba4b5] hover:bg-[#4a91a2] text-slate-900 px-4 py-2.5 h-[44px] flex items-center justify-center transition disabled:opacity-50 flex-shrink-0"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Concept Cards Sidebar */}
        <div className="space-y-6">
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-md font-bold text-slate-200 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-[#5ba4b5]" /> Concept Quick Cards
            </h3>
            <p className="text-xs text-slate-400">
              Click on any core term to get a structured Socratic explanation card.
            </p>
            <div className="grid grid-cols-2 gap-2">
              {conceptsList.map(concept => (
                <button
                  key={concept}
                  onClick={() => handleExplainConcept(concept)}
                  className={`text-xs p-2.5 rounded-lg border text-center transition ${
                    selectedConcept === concept
                      ? 'bg-[#5ba4b5]/10 border-[#5ba4b5] text-[#5ba4b5]'
                      : 'bg-[#12141c]/50 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  {concept}
                </button>
              ))}
            </div>
          </div>

          {selectedConcept && (
            <div className="glass-card p-6 space-y-4 bg-gradient-to-br from-[#1a1d28] to-[#12141c] border-l-4 border-l-[#5ba4b5]">
              <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                <h4 className="font-bold text-sm text-slate-200">{selectedConcept}</h4>
                <button onClick={() => setSelectedConcept(null)} className="text-slate-500 hover:text-slate-400 text-xs">
                  Close
                </button>
              </div>
              {loadingConcept ? (
                <div className="text-xs text-slate-500 animate-pulse flex items-center gap-2 py-4">
                  <Loader className="h-3 w-3 animate-spin" /> Fetching card details...
                </div>
              ) : (
                <div className="text-xs text-slate-400 leading-relaxed whitespace-pre-line font-sans">
                  {conceptExplanation}
                </div>
              )}
            </div>
          )}

          {/* Sessions quick-access panel (when in chat mode) */}
          {panelView === 'chat' && sessions.length > 0 && (
            <div className="glass-card p-5 space-y-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Clock className="h-4 w-4 text-[#5ba4b5]" /> Recent Sessions
              </h3>
              <div className="space-y-1.5">
                {sessions.slice(0, 4).map(session => (
                  <button
                    key={session.id}
                    onClick={() => handleLoadSession(session.id)}
                    className={`w-full text-left text-xs px-3 py-2.5 rounded-lg border transition group flex items-center justify-between ${
                      currentSessionId === session.id
                        ? 'bg-[#5ba4b5]/10 border-[#5ba4b5]/40 text-[#5ba4b5]'
                        : 'border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                    }`}
                  >
                    <span className="truncate">{session.title}</span>
                    <ChevronRight className="h-3 w-3 flex-shrink-0 ml-1 opacity-50 group-hover:opacity-100" />
                  </button>
                ))}
                {sessions.length > 4 && (
                  <button
                    onClick={() => { setPanelView('sessions'); loadSessions(); }}
                    className="w-full text-center text-[10px] text-slate-500 hover:text-slate-400 transition py-1"
                  >
                    View all {sessions.length} sessions →
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
