'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Send, Trash2, Settings2, Bot, User, Columns2 } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  model?: string
}

function ChatBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
        isUser ? 'bg-primary/10' : 'bg-white/10'
      }`}>
        {isUser ? <User className="h-4 w-4 text-primary" /> : <Bot className="h-4 w-4 text-muted-foreground" />}
      </div>
      <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
        isUser
          ? 'bg-primary/10 border border-primary/20'
          : 'bg-white/5 border border-white/10'
      }`}>
        <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">{msg.content}</pre>
      </div>
    </div>
  )
}

function StreamingBubble({ content }: { content: string }) {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-white/10">
        <Bot className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="max-w-[75%] rounded-2xl px-4 py-3 text-sm bg-white/5 border border-white/10">
        <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">{content}<span className="inline-block w-2 h-4 bg-primary/60 animate-pulse ml-0.5 rounded-sm" /></pre>
      </div>
    </div>
  )
}

export default function PlaygroundPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [compareMessages, setCompareMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [model, setModel] = useState('')
  const [compareModel, setCompareModel] = useState('')
  const [models, setModels] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(2048)
  const [ragEnabled, setRagEnabled] = useState(false)
  const [compareMode, setCompareMode] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch('/api/playground/models')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) {
          const names = data.map((m: any) => m.name)
          setModels(names)
          if (names.length > 0) setModel(names[0])
          if (names.length > 1) setCompareModel(names[1])
        }
      })
      .catch(() => setModels([]))
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const sendMessage = async () => {
    if (!input.trim() || !model || loading) return
    const userMsg: Message = { role: 'user', content: input.trim() }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setLoading(true)
    setStreamingContent('')

    const apiMessages = newMessages.map(m => ({ role: m.role, content: m.content }))

    try {
      const resp = await fetch('/api/playground/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, messages: apiMessages, temperature, max_tokens: maxTokens, stream: true, rag_enabled: ragEnabled }),
      })
      const reader = resp.body?.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''
      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const lines = decoder.decode(value).split('\n')
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') continue
              try {
                const parsed = JSON.parse(data)
                if (parsed.token) { fullContent += parsed.token; setStreamingContent(fullContent) }
              } catch {}
            }
          }
        }
      }
      setMessages(prev => [...prev, { role: 'assistant', content: fullContent, model }])
      setStreamingContent('')
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e}`, model }])
      setStreamingContent('')
    }

    if (compareMode && compareModel && compareModel !== model) {
      try {
        const resp = await fetch('/api/playground/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: compareModel, messages: apiMessages, temperature, max_tokens: maxTokens, stream: false, rag_enabled: ragEnabled }),
        })
        const data = await resp.json()
        setCompareMessages(prev => [...prev, userMsg, { role: 'assistant', content: data.content || data.error || 'No response', model: compareModel }])
      } catch (e) {
        setCompareMessages(prev => [...prev, userMsg, { role: 'assistant', content: `Error: ${e}`, model: compareModel }])
      }
    }
    setLoading(false)
  }

  const ChatPanel = ({ msgs, streaming, modelName }: { msgs: Message[]; streaming: string; modelName: string }) => (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-3 px-1">
        <Bot className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium text-primary">{modelName || 'No model'}</span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {msgs.map((msg, i) => <ChatBubble key={i} msg={msg} />)}
        {streaming && <StreamingBubble content={streaming} />}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 bg-white/5 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <select value={model} onChange={e => setModel(e.target.value)}
            className="bg-background border border-white/10 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-primary">
            {models.length === 0 && <option value="">No models</option>}
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          <Button variant={compareMode ? 'default' : 'ghost'} size="sm"
            onClick={() => { setCompareMode(!compareMode); setCompareMessages([]) }}>
            <Columns2 className="mr-1.5 h-3.5 w-3.5" /> Compare
          </Button>
          {compareMode && (
            <select value={compareModel} onChange={e => setCompareModel(e.target.value)}
              className="bg-background border border-white/10 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-primary">
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant={ragEnabled ? 'default' : 'ghost'} size="sm" onClick={() => setRagEnabled(!ragEnabled)}>
            RAG {ragEnabled ? 'ON' : 'OFF'}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setShowSettings(!showSettings)}>
            <Settings2 className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => { setMessages([]); setCompareMessages([]); setStreamingContent('') }}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Settings panel */}
      {showSettings && (
        <div className="px-4 py-3 border-b border-white/10 bg-white/5 flex items-center gap-8">
          <label className="flex items-center gap-3 text-xs text-muted-foreground">
            Temperature
            <input type="range" min="0" max="2" step="0.1" value={temperature} onChange={e => setTemperature(parseFloat(e.target.value))}
              className="w-28 accent-primary" />
            <span className="text-primary font-semibold w-8">{temperature}</span>
          </label>
          <label className="flex items-center gap-3 text-xs text-muted-foreground">
            Max Tokens
            <input type="range" min="256" max="8192" step="256" value={maxTokens} onChange={e => setMaxTokens(parseInt(e.target.value))}
              className="w-28 accent-primary" />
            <span className="text-primary font-semibold w-12">{maxTokens}</span>
          </label>
        </div>
      )}

      {/* Chat area */}
      <div className="flex-1 overflow-hidden flex">
        <div className={`flex-1 p-4 ${compareMode ? 'border-r border-white/10' : ''}`}>
          <ChatPanel msgs={messages} streaming={streamingContent} modelName={model} />
        </div>
        {compareMode && (
          <div className="flex-1 p-4">
            <ChatPanel msgs={compareMessages} streaming="" modelName={compareModel} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-white/10 bg-white/5 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto flex gap-3">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Type your message..."
            disabled={loading || !model}
            className="flex-1 bg-background border border-white/10 rounded-xl px-4 py-3 text-sm placeholder-muted-foreground focus:outline-none focus:border-primary disabled:opacity-50 transition-colors"
          />
          <Button onClick={sendMessage} disabled={loading || !input.trim() || !model} size="lg">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
