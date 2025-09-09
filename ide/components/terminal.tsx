"use client"

import type React from "react"
import { useState, useRef, useEffect } from "react"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { Trash2, Copy, Download } from "lucide-react"

interface TerminalLine {
  type: "command" | "output" | "error"
  content: string
  timestamp: Date
}

export function Terminal() {
  const [lines, setLines] = useState<TerminalLine[]>([])
  const [currentCommand, setCurrentCommand] = useState("")
  const [commandHistory, setCommandHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const terminalRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // Conexión WebSocket al backend
    const ws = new WebSocket("ws://localhost:8765")
    ws.onopen = () => {
      setLines((prev) => [
        ...prev,
        { type: "output", content: "Conectado a la terminal real", timestamp: new Date() },
      ])
    }
    ws.onmessage = (event) => {
      setLines((prev) => [
        ...prev,
        { type: "output", content: event.data, timestamp: new Date() },
      ])
    }
    ws.onerror = () => {
      setLines((prev) => [
        ...prev,
        { type: "error", content: "Error de conexión con el servidor", timestamp: new Date() },
      ])
    }
    ws.onclose = () => {
      setLines((prev) => [
        ...prev,
        { type: "error", content: "Conexión cerrada", timestamp: new Date() },
      ])
    }

    wsRef.current = ws
    return () => ws.close()
  }, [])

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [lines])

  const executeCommand = (command: string) => {
    const trimmedCommand = command.trim()
    if (!trimmedCommand) return

    // Historial
    setCommandHistory((prev) => [...prev, trimmedCommand])
    setHistoryIndex(-1)

    // Mostrar el comando en la terminal
    setLines((prev) => [
      ...prev,
      { type: "command", content: `$ ${trimmedCommand}`, timestamp: new Date() },
    ])

    // Mandar al servidor WebSocket
    wsRef.current?.send(trimmedCommand)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      executeCommand(currentCommand)
      setCurrentCommand("")
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      if (commandHistory.length > 0) {
        const newIndex = historyIndex === -1 ? commandHistory.length - 1 : Math.max(0, historyIndex - 1)
        setHistoryIndex(newIndex)
        setCurrentCommand(commandHistory[newIndex])
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault()
      if (historyIndex !== -1) {
        const newIndex = historyIndex + 1
        if (newIndex >= commandHistory.length) {
          setHistoryIndex(-1)
          setCurrentCommand("")
        } else {
          setHistoryIndex(newIndex)
          setCurrentCommand(commandHistory[newIndex])
        }
      }
    }
  }

  const clearTerminal = () => setLines([])
  const copyOutput = () => navigator.clipboard.writeText(lines.map((l) => l.content).join("\n"))
  const downloadLog = () => {
    const output = lines
      .map((line) => `[${line.timestamp.toLocaleTimeString()}] ${line.type.toUpperCase()}: ${line.content}`)
      .join("\n")
    const blob = new Blob([output], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "terminal-log.txt"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex-1 flex flex-col bg-background">
      {/* Toolbar */}
      <div className="h-10 bg-card border-b border-border flex items-center px-3 gap-2">
        <Button variant="ghost" size="sm" onClick={clearTerminal} className="h-7 px-2">
          <Trash2 className="h-3 w-3 mr-1" /> Clear
        </Button>
        <Button variant="ghost" size="sm" onClick={copyOutput} className="h-7 px-2">
          <Copy className="h-3 w-3 mr-1" /> Copy
        </Button>
        <Button variant="ghost" size="sm" onClick={downloadLog} className="h-7 px-2">
          <Download className="h-3 w-3 mr-1" /> Log
        </Button>
      </div>

      {/* Terminal output */}
      <div ref={terminalRef} className="flex-1 overflow-auto p-4 font-mono text-sm bg-background">
        {lines.map((line, index) => (
          <div key={index} className="mb-1">
            <span
              className={
                line.type === "command"
                  ? "text-primary"
                  : line.type === "error"
                  ? "text-destructive"
                  : "text-foreground"
              }
            >
              {line.content}
            </span>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="border-t border-border p-4">
        <div className="flex items-center gap-2">
          <span className="text-primary font-mono text-sm">$</span>
          <Input
            ref={inputRef}
            value={currentCommand}
            onChange={(e) => setCurrentCommand(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command..."
            className="font-mono text-sm bg-background border-0 focus-visible:ring-0 px-0"
            autoFocus
          />
        </div>
      </div>
    </div>
  )
}
