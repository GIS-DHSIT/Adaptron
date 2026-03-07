'use client'

import { useState, useRef, useEffect } from 'react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  model?: string
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
  const [streamingContent, setStreamingContent] = useState('')
  const [compareStreamingContent, setCompareStreamingContent] = useState('')
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
    setCompareStreamingContent('')

    const apiMessages = newMessages.map(m => ({ role: m.role, content: m.content }))

    // Primary model - streaming
    try {
      const resp = await fetch('/api/playground/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          messages: apiMessages,
          temperature,
          max_tokens: maxTokens,
          stream: true,
          rag_enabled: ragEnabled,
        }),
      })

      const reader = resp.body?.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const text = decoder.decode(value)
          const lines = text.split('\n')
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') continue
              try {
                const parsed = JSON.parse(data)
                if (parsed.token) {
                  fullContent += parsed.token
                  setStreamingContent(fullContent)
                }
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

    // Compare model (non-streaming for simplicity)
    if (compareMode && compareModel && compareModel !== model) {
      try {
        const resp = await fetch('/api/playground/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: compareModel,
            messages: apiMessages,
            temperature,
            max_tokens: maxTokens,
            stream: false,
            rag_enabled: ragEnabled,
          }),
        })
        const data = await resp.json()
        setCompareMessages(prev => [
          ...prev,
          { role: 'user', content: userMsg.content },
          { role: 'assistant', content: data.content || data.error || 'No response', model: compareModel },
        ])
      } catch (e) {
        setCompareMessages(prev => [
          ...prev,
          { role: 'user', content: userMsg.content },
          { role: 'assistant', content: `Error: ${e}`, model: compareModel },
        ])
      }
    }

    setLoading(false)
  }

  const clearChat = () => {
    setMessages([])
    setCompareMessages([])
    setStreamingContent('')
    setCompareStreamingContent('')
  }

  const ChatPanel = ({ msgs, streaming, title, modelName }: { msgs: Message[], streaming: string, title: string, modelName: string }) => (
    <div className="flex flex-col h-full">
      <div className="text-xs text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-2">
        <span>{title}</span>
        <span className="text-accent font-bold">{modelName}</span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
        {msgs.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
              msg.role === 'user'
                ? 'bg-accent/20 border border-accent/30 text-white'
                : 'bg-surface border border-border text-gray-300'
            }`}>
              <pre className="whitespace-pre-wrap font-mono text-xs">{msg.content}</pre>
            </div>
          </div>
        ))}
        {streaming && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-xl px-4 py-3 text-sm bg-surface border border-border text-gray-300">
              <pre className="whitespace-pre-wrap font-mono text-xs">{streaming}<span className="animate-pulse">|</span></pre>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="bg-surface border-b border-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-accent to-purple rounded-lg flex items-center justify-center text-sm">&#x1F9EA;</div>
          <div>
            <div className="text-sm font-bold uppercase tracking-wider">Playground</div>
            <div className="text-xs text-gray-500">Test your finetuned model</div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Model selector */}
          <select
            value={model}
            onChange={e => setModel(e.target.value)}
            className="bg-bg border border-border rounded-lg px-3 py-1.5 text-sm text-white"
          >
            {models.length === 0 && <option value="">No models available</option>}
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>

          {/* Compare toggle */}
          <button
            onClick={() => { setCompareMode(!compareMode); setCompareMessages([]) }}
            className={`px-3 py-1.5 rounded-lg text-xs uppercase tracking-wider font-bold border ${
              compareMode ? 'bg-purple/20 border-purple/40 text-purple' : 'border-border text-gray-500 hover:text-white'
            }`}
          >
            Compare
          </button>

          {/* Compare model selector */}
          {compareMode && (
            <select
              value={compareModel}
              onChange={e => setCompareModel(e.target.value)}
              className="bg-bg border border-border rounded-lg px-3 py-1.5 text-sm text-white"
            >
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          )}

          {/* RAG toggle */}
          <button
            onClick={() => setRagEnabled(!ragEnabled)}
            className={`px-3 py-1.5 rounded-lg text-xs uppercase tracking-wider font-bold border ${
              ragEnabled ? 'bg-green/20 border-green/40 text-green' : 'border-border text-gray-500 hover:text-white'
            }`}
          >
            RAG {ragEnabled ? 'ON' : 'OFF'}
          </button>

          {/* Clear */}
          <button onClick={clearChat} className="px-3 py-1.5 rounded-lg text-xs border border-border text-gray-500 hover:text-white uppercase">
            Clear
          </button>
        </div>
      </div>

      {/* Controls bar */}
      <div className="bg-surface/50 border-b border-border px-6 py-2 flex items-center gap-6">
        <label className="flex items-center gap-2 text-xs text-gray-400">
          Temperature
          <input type="range" min="0" max="2" step="0.1" value={temperature} onChange={e => setTemperature(parseFloat(e.target.value))} className="w-24 accent-accent" />
          <span className="text-accent font-bold w-8">{temperature}</span>
        </label>
        <label className="flex items-center gap-2 text-xs text-gray-400">
          Max Tokens
          <input type="range" min="256" max="8192" step="256" value={maxTokens} onChange={e => setMaxTokens(parseInt(e.target.value))} className="w-24 accent-accent" />
          <span className="text-accent font-bold w-12">{maxTokens}</span>
        </label>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-hidden flex">
        <div className={`flex-1 p-6 ${compareMode ? 'border-r border-border' : ''}`}>
          <ChatPanel msgs={messages} streaming={streamingContent} title="Primary" modelName={model || 'none'} />
        </div>
        {compareMode && (
          <div className="flex-1 p-6">
            <ChatPanel msgs={compareMessages} streaming={compareStreamingContent} title="Compare" modelName={compareModel || 'none'} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="bg-surface border-t border-border p-4">
        <div className="max-w-4xl mx-auto flex gap-3">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Type your message..."
            disabled={loading || !model}
            className="flex-1 bg-bg border border-border rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:border-accent focus:outline-none disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim() || !model}
            className="px-6 py-3 bg-accent text-white rounded-xl font-bold text-sm uppercase disabled:bg-border disabled:text-gray-600 shadow-lg shadow-accent/20 hover:opacity-90"
          >
            {loading ? '...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
