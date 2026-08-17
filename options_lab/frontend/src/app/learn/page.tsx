'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { optionsApi } from '@/lib/api';
import {
  BookOpen, Send, Sparkles, Loader, Save, Clock, Trash2,
  FolderOpen, PlusCircle, Check, ChevronRight, ChevronDown, X,
  Lightbulb, Globe
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
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        "Hello! I am your Socratic Options & Markets Tutor. I act as your Senior Financial Analyst and Research Assistant. I'm here to help you explore corporate finance, risk exposure, earnings, capital allocation, and market strategy. What concepts or portfolio events are you analyzing today?"
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [enableGrounding, setEnableGrounding] = useState(false);
  const [hintText, setHintText] = useState<string | null>(null);
  const [loadingHint, setLoadingHint] = useState(false);

  const [selectedConcept, setSelectedConcept] = useState<string | null>(null);
  const [conceptExplanation, setConceptExplanation] = useState<string>('');
  const [loadingConcept, setLoadingConcept] = useState(false);

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

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput('');
    setLoading(true);
    setHintText(null);

    try {
      const chatHistory = messages.map(m => ({ role: m.role, content: m.content }));
      const res = await optionsApi.askTutor({
        message: text,
        chat_history: chatHistory,
        enable_grounding: enableGrounding
      });
      const newMessages = [...updatedMessages, { role: 'assistant' as const, content: res.response }];
      setMessages(newMessages);

      if (currentSessionId) {
        await optionsApi.updateSession(currentSessionId, newMessages);
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

  const handleRequestHint = async () => {
    if (loadingHint) return;
    setLoadingHint(true);
    try {
      const chatHistory = messages.map(m => ({ role: m.role, content: m.content }));
      const res = await optionsApi.getTutorHint({ chat_history: chatHistory });
      setHintText(res.hint);
    } catch (err) {
      console.error(err);
      setHintText("💡 **Hint:** Consider the direction of your Delta exposure and how time decay (Theta) accelerates near expiration.");
    } finally {
      setLoadingHint(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend(input);
    }
  };

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

  const handleSaveSession = async () => {
    if (messages.length <= 1) return;
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
    startOfWeek.setDate(now.getDate() - now.getDay());

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
    "How does Arnott's Fundamental Indexation eliminate the 20% cap-weight drag?",
    "How can I use Fundamental Weight (W_fund) vs Cap Weight (W_cap) to structure options overlay trades?",
    "How do companies decide between stock buybacks and dividends?",
    "What is capital allocation and why does ROI matter?"
  ];

  const conceptsList = [
    "Fundamental Indexation", "Cap-Weight Drag", "Capital Allocation",
    "Risk Exposure", "Corporate Earnings", "Hedging Options"
  ];

  const groupedSessions = getGroupedSessions();

  return (
    <ProtectedRoute>
      <div className="space-y-6 pb-12">
        {/* Banner Header - Velzon Light Theme */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-[#4051B5] border border-indigo-100">
              <BookOpen className="h-3.5 w-3.5" /> Socratic AI Analyst & Tutor
            </span>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
              Socratic Financial <span className="text-[#4051B5]">Tutor</span>
            </h1>
            <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
              Deepen your quantitative understanding of corporate finance, capital allocation, options strategies, and Arnott&apos;s Fundamental Indexation through interactive Socratic dialog.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {currentSessionId && (
              <span className="text-[10px] bg-indigo-50 text-[#4051B5] border border-indigo-200 rounded-full px-2.5 py-1 font-bold">
                Session Active
              </span>
            )}
            <button
              onClick={handleNewChat}
              className="flex items-center gap-1.5 text-xs px-3.5 py-2 rounded-lg bg-white border border-slate-200 text-slate-700 font-bold hover:bg-slate-50 transition shadow-sm"
            >
              <PlusCircle className="h-3.5 w-3.5" /> New Chat
            </button>
            <button
              onClick={() => { setPanelView(panelView === 'sessions' ? 'chat' : 'sessions'); loadSessions(); }}
              className={`flex items-center gap-1.5 text-xs px-3.5 py-2 rounded-lg border transition font-bold shadow-sm ${
                panelView === 'sessions'
                  ? 'bg-[#4051B5] border-[#4051B5] text-white'
                  : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <Clock className="h-3.5 w-3.5" />
              Saved Sessions {sessions.length > 0 && <span className="ml-1 bg-indigo-50 text-[#4051B5] rounded-full px-1.5 text-[10px]">{sessions.length}</span>}
            </button>
          </div>
        </div>

        {/* Sessions Panel */}
        {panelView === 'sessions' && (
          <div className="p-6 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                <FolderOpen className="h-4 w-4 text-[#4051B5]" /> Saved Learning Sessions
              </h2>
              <button onClick={() => setPanelView('chat')} className="text-slate-400 hover:text-slate-600 transition">
                <X className="h-4 w-4" />
              </button>
            </div>
            
            {sessionsLoading ? (
              <div className="flex items-center gap-2 text-xs text-slate-400 animate-pulse py-4">
                <Loader className="h-3.5 w-3.5 animate-spin" /> Loading sessions...
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-xs">
                <BookOpen className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                <p>No saved sessions yet.</p>
                <p className="mt-1 text-slate-500">Start a conversation and click <strong className="text-slate-700">Save Session</strong> to persist it.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {Object.entries(groupedSessions).map(([groupName, groupItems]) => (
                  <div key={groupName} className="space-y-2">
                    <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 pb-1">
                      {groupName}
                    </h3>
                    <div className="divide-y divide-slate-100">
                      {groupItems.map(session => (
                        <div key={session.id} className="py-2">
                          <div 
                            className={`flex items-center justify-between hover:bg-slate-50 rounded-lg px-3 py-2 transition group ${
                              currentSessionId === session.id ? 'bg-indigo-50/60 border-l-4 border-[#4051B5]' : ''
                            }`}
                          >
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setExpandedSessionId(expandedSessionId === session.id ? null : session.id);
                                }}
                                className="p-1 rounded hover:bg-slate-200 text-slate-400 hover:text-slate-700 transition"
                                title="Toggle Key Learnings"
                              >
                                {expandedSessionId === session.id ? (
                                  <ChevronDown className="h-4 w-4 text-[#4051B5]" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </button>
                              
                              <div 
                                onClick={() => handleLoadSession(session.id)}
                                className="flex-1 cursor-pointer min-w-0"
                              >
                                <p className="text-xs text-slate-800 font-bold truncate hover:text-[#4051B5] transition">
                                  {session.title}
                                </p>
                                <p className="text-[10px] text-slate-400 font-mono">
                                  Updated: {formatDate(session.updated_at)}
                                </p>
                              </div>
                            </div>

                            <div className="flex items-center gap-2 ml-3">
                              <button
                                onClick={() => handleLoadSession(session.id)}
                                className="text-[10px] text-slate-700 bg-slate-100 hover:bg-indigo-50 hover:text-[#4051B5] border border-slate-200 px-2.5 py-1 rounded-lg transition font-bold"
                              >
                                Load Chat
                              </button>
                              <button
                                onClick={(e) => handleDeleteSession(session.id, e)}
                                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition opacity-0 group-hover:opacity-100"
                                title="Delete Session"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </div>

                          {expandedSessionId === session.id && (
                            <div className="ml-9 mt-2 p-3.5 rounded-xl border border-indigo-100 bg-indigo-50/40 space-y-2">
                              <span className="text-[10px] font-bold text-[#4051B5] uppercase tracking-wider block">
                                Key Financial Learnings
                              </span>
                              {session.key_learnings ? (
                                <ul className="list-disc list-inside space-y-1.5 text-slate-700 text-xs">
                                  {session.key_learnings.split('\n').filter(line => line.trim().startsWith('-')).map((line, idx) => (
                                    <li key={idx} className="leading-relaxed pl-1 font-medium">
                                      {line.replace(/^-\s*/, '')}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="text-slate-400 text-xs italic">No key learnings extracted yet.</p>
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

        {/* Save Dialog */}
        {showSaveDialog && (
          <div className="p-5 border border-indigo-200 bg-white rounded-xl shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-800">Save Session</h3>
            <input
              type="text"
              value={sessionTitle}
              onChange={e => setSessionTitle(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSaveSession()}
              placeholder="Give this session a title..."
              autoFocus
              className="w-full rounded-lg px-4 py-2 text-xs bg-slate-50 border border-slate-200 font-medium text-slate-800"
            />
            <div className="flex gap-2">
              <button
                onClick={handleSaveSession}
                disabled={saveStatus === 'saving'}
                className="flex items-center gap-1.5 text-xs px-4 py-2 rounded-lg bg-[#4051B5] hover:bg-[#34449a] text-white font-semibold transition disabled:opacity-60"
              >
                {saveStatus === 'saving' ? <Loader className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                {saveStatus === 'saving' ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={() => { setShowSaveDialog(false); setSessionTitle(''); }}
                className="text-xs px-3 py-2 rounded-lg border border-slate-200 text-slate-600 hover:text-slate-800 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Main Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Chat Window */}
          <div className="lg:col-span-2 flex flex-col h-[600px] border border-slate-200/80 bg-white rounded-xl shadow-sm overflow-hidden">
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((m, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 max-w-[85%] ${
                    m.role === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
                  }`}
                >
                  <div className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                    m.role === 'user' ? 'bg-indigo-100 text-[#4051B5]' : 'bg-emerald-100 text-emerald-700'
                  }`}>
                    {m.role === 'user' ? 'U' : 'AI'}
                  </div>
                  <div className={`p-4 rounded-2xl text-xs leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-[#4051B5] text-white rounded-tr-none font-medium shadow-sm'
                      : 'bg-slate-50 text-slate-800 rounded-tl-none border border-slate-200/80 font-medium'
                  }`}>
                    <div className="whitespace-pre-line prose max-w-none text-xs">
                      {m.content}
                    </div>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex gap-3 mr-auto items-center text-xs text-slate-500 animate-pulse">
                  <Loader className="h-4 w-4 animate-spin text-[#4051B5]" />
                  Tutor is formulating response...
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Quick Prompts */}
            {messages.length === 1 && (
              <div className="px-6 py-3 border-t border-slate-100 bg-slate-50/50">
                <span className="text-[10px] text-slate-400 font-bold block mb-2 uppercase tracking-wider">
                  Suggested Learning Topics
                </span>
                <div className="grid gap-2">
                  {quickPrompts.map(prompt => (
                    <button
                      key={prompt}
                      onClick={() => handleSend(prompt)}
                      className="text-left text-xs text-slate-600 hover:text-[#4051B5] hover:bg-indigo-50/50 p-2 rounded-lg transition border border-slate-200/60 font-medium"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Hint Callout Box */}
            {hintText && (
              <div className="mx-6 mb-3 p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2.5 text-xs text-amber-800">
                <Lightbulb className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1 whitespace-pre-line">{hintText}</div>
                <button onClick={() => setHintText(null)} className="text-amber-600 hover:text-amber-800">
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            )}

            {/* Input Bar */}
            <div className="p-4 border-t border-slate-100 bg-white">
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-3">
                  {messages.length > 1 && (
                    saveStatus === 'saved' ? (
                      <span className="flex items-center gap-1 text-[10px] text-emerald-600 font-bold">
                        <Check className="h-3 w-3" /> Saved
                      </span>
                    ) : (
                      <button
                        onClick={() => setShowSaveDialog(true)}
                        disabled={saveStatus === 'saving'}
                        className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-[#4051B5] transition font-bold"
                      >
                        <Save className="h-3 w-3" />
                        {currentSessionId ? 'Update Session' : 'Save Session'}
                      </button>
                    )
                  )}

                  <button
                    onClick={handleRequestHint}
                    disabled={loadingHint}
                    className="flex items-center gap-1 text-[10px] px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 transition disabled:opacity-50 font-bold"
                  >
                    {loadingHint ? <Loader className="h-3 w-3 animate-spin text-amber-600" /> : <Lightbulb className="h-3 w-3 text-amber-600" />}
                    Request Hint
                  </button>
                </div>

                <label className="flex items-center gap-1.5 text-[10px] text-slate-500 cursor-pointer font-bold hover:text-slate-800 transition">
                  <input
                    type="checkbox"
                    checked={enableGrounding}
                    onChange={e => setEnableGrounding(e.target.checked)}
                    className="rounded border-slate-300 text-[#4051B5] focus:ring-0"
                  />
                  <Globe className={`h-3 w-3 ${enableGrounding ? 'text-[#4051B5]' : 'text-slate-400'}`} />
                  <span>Search Grounding</span>
                </label>
              </div>
              <div className="flex gap-2 items-end">
                <textarea
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask your analyst tutor... (Ctrl+Enter to send)"
                  rows={2}
                  className="flex-1 rounded-lg px-3.5 py-2 text-xs bg-slate-50 text-slate-800 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition min-h-[44px] max-h-[160px] overflow-y-auto resize-none font-medium"
                />
                <button
                  onClick={() => handleSend(input)}
                  disabled={loading}
                  className="rounded-lg bg-[#4051B5] hover:bg-[#34449a] text-white px-4 py-2.5 h-[44px] flex items-center justify-center transition disabled:opacity-50 flex-shrink-0 shadow-sm"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Concept Cards Sidebar */}
          <div className="space-y-6">
            <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
              <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-[#4051B5]" /> Concept Quick Cards
              </h3>
              <p className="text-xs text-slate-500 font-medium">
                Click on any core term to get a structured Socratic explanation card.
              </p>
              <div className="grid grid-cols-2 gap-2">
                {conceptsList.map(concept => (
                  <button
                    key={concept}
                    onClick={() => handleExplainConcept(concept)}
                    className={`text-xs p-2.5 rounded-lg border text-center transition font-bold ${
                      selectedConcept === concept
                        ? 'bg-indigo-50 border-[#4051B5] text-[#4051B5]'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300'
                    }`}
                  >
                    {concept}
                  </button>
                ))}
              </div>
            </div>

            {selectedConcept && (
              <div className="p-6 border-l-4 border-l-[#4051B5] border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-3">
                <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                  <h4 className="font-bold text-sm text-slate-800">{selectedConcept}</h4>
                  <button onClick={() => setSelectedConcept(null)} className="text-slate-400 hover:text-slate-600 text-xs">
                    Close
                  </button>
                </div>
                {loadingConcept ? (
                  <div className="text-xs text-slate-400 animate-pulse flex items-center gap-2 py-4">
                    <Loader className="h-3.5 w-3.5 animate-spin" /> Fetching card details...
                  </div>
                ) : (
                  <div className="text-xs text-slate-600 leading-relaxed whitespace-pre-line font-sans font-medium">
                    {conceptExplanation}
                  </div>
                )}
              </div>
            )}

            {/* Sessions Quick Access Panel */}
            {panelView === 'chat' && sessions.length > 0 && (
              <div className="p-5 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-3">
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <Clock className="h-4 w-4 text-[#4051B5]" /> Recent Sessions
                </h3>
                <div className="space-y-1.5">
                  {sessions.slice(0, 4).map(session => (
                    <button
                      key={session.id}
                      onClick={() => handleLoadSession(session.id)}
                      className={`w-full text-left text-xs px-3 py-2 rounded-lg border transition group flex items-center justify-between font-medium ${
                        currentSessionId === session.id
                          ? 'bg-indigo-50 border-indigo-200 text-[#4051B5] font-bold'
                          : 'border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300'
                      }`}
                    >
                      <span className="truncate">{session.title}</span>
                      <ChevronRight className="h-3.5 w-3.5 flex-shrink-0 ml-1 opacity-50 group-hover:opacity-100" />
                    </button>
                  ))}
                  {sessions.length > 4 && (
                    <button
                      onClick={() => { setPanelView('sessions'); loadSessions(); }}
                      className="w-full text-center text-[11px] text-slate-500 font-bold hover:text-[#4051B5] transition py-1"
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
