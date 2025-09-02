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
  const [lines, setLines] = useState<TerminalLine[]>([
    {
      type: "output",
      content: "Simple IDE Terminal v1.0.0",
      timestamp: new Date(),
    },
    {
      type: "output",
      content: 'Type "help" for available commands',
      timestamp: new Date(),
    },
  ])
  const [currentCommand, setCurrentCommand] = useState("")
  const [commandHistory, setCommandHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const terminalRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Auto-scroll to bottom when new lines are added
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [lines])

  const executeCommand = (command: string) => {
    const trimmedCommand = command.trim()
    if (!trimmedCommand) return

    // Add command to history
    setCommandHistory((prev) => [...prev, trimmedCommand])
    setHistoryIndex(-1)

    // Add command line
    setLines((prev) => [
      ...prev,
      {
        type: "command",
        content: `$ ${trimmedCommand}`,
        timestamp: new Date(),
      },
    ])

    // Process command
    const [cmd, ...args] = trimmedCommand.split(" ")
    let output = ""
    let isError = false

    switch (cmd.toLowerCase()) {
      case "help":
        output = `Available commands:
  help          - Show this help message
  clear         - Clear terminal
  echo [text]   - Echo text
  date          - Show current date and time
  pwd           - Show current directory
  ls            - List files (simulated)
  cat [file]    - Show file content (simulated)
  node [file]   - Run JavaScript file (simulated)
  npm [command] - Run npm command (simulated)`
        break

      case "clear":
        setLines([])
        return

      case "echo":
        output = args.join(" ")
        break

      case "date":
        output = new Date().toString()
        break

      case "pwd":
        output = "/workspace/simple-ide"
        break

      case "ls":
        output = `src/
public/
package.json
README.md`
        break

      case "cat":
        if (args.length === 0) {
          output = "cat: missing file operand"
          isError = true
        } else {
          output = `// Content of ${args[0]}
// This is a simulated file content
console.log("Hello from ${args[0]}");`
        }
        break

      case "node":
        if (args.length === 0) {
          output = "node: missing file operand"
          isError = true
        } else {
          output = `Running ${args[0]}...
Hello from ${args[0]}
Process completed successfully`
        }
        break

      case "npm":
        if (args.length === 0) {
          output = "npm: missing command"
          isError = true
        } else {
          output = `npm ${args.join(" ")}
✓ Command executed successfully (simulated)`
        }
        break

      default:
        output = `Command not found: ${cmd}. Type "help" for available commands.`
        isError = true
    }

    // Add output
    if (output) {
      setLines((prev) => [
        ...prev,
        {
          type: isError ? "error" : "output",
          content: output,
          timestamp: new Date(),
        },
      ])
    }
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

  const clearTerminal = () => {
    setLines([])
  }

  const copyOutput = () => {
    const output = lines.map((line) => line.content).join("\n")
    navigator.clipboard.writeText(output)
  }

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
      {/* Terminal toolbar */}
      <div className="h-10 bg-card border-b border-border flex items-center px-3 gap-2">
        <Button variant="ghost" size="sm" onClick={clearTerminal} className="h-7 px-2">
          <Trash2 className="h-3 w-3 mr-1" />
          Clear
        </Button>
        <Button variant="ghost" size="sm" onClick={copyOutput} className="h-7 px-2">
          <Copy className="h-3 w-3 mr-1" />
          Copy
        </Button>
        <Button variant="ghost" size="sm" onClick={downloadLog} className="h-7 px-2">
          <Download className="h-3 w-3 mr-1" />
          Log
        </Button>
      </div>

      {/* Terminal output */}
      <div ref={terminalRef} className="flex-1 overflow-auto p-4 font-mono text-sm bg-background">
        {lines.map((line, index) => (
          <div key={index} className="mb-1">
            <span
              className={`${
                line.type === "command"
                  ? "text-primary"
                  : line.type === "error"
                    ? "text-destructive"
                    : "text-foreground"
              }`}
            >
              {line.content}
            </span>
          </div>
        ))}
      </div>

      {/* Command input */}
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
