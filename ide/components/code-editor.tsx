"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { Button } from "./ui/button"
import { Save, Play, Copy, Download } from "lucide-react"
import { cn } from "@/lib/utils"

interface CodeError {
  line: number
  column: number
  message: string
}

interface CodeEditorProps {
  activeFile: string | null
  content: string
  onContentChange: (filePath: string, content: string) => void
}

export function CodeEditor({ activeFile, content, onContentChange }: CodeEditorProps) {
  const [localContent, setLocalContent] = useState(content)
  const [lineCount, setLineCount] = useState(1)
  const [errors, setErrors] = useState<CodeError[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const highlightRef = useRef<HTMLPreElement>(null)
  const websocketRef = useRef<WebSocket | null>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    setLocalContent(content)
  }, [content])

  useEffect(() => {
    const lines = localContent.split("\n").length
    setLineCount(lines)
  }, [localContent])

  // Conectar al WebSocket
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const ws = new WebSocket("ws://localhost:8765")
        
        ws.onopen = () => {
          console.log("Conectado al WebSocket")
          setIsConnected(true)
          websocketRef.current = ws
        }
        
        ws.onmessage = (event) => {
          const response = event.data
          console.log("Respuesta del servidor:", response)
          parseErrors(response)
        }
        
        ws.onclose = () => {
          console.log("Desconectado del WebSocket")
          setIsConnected(false)
          websocketRef.current = null
          // Intentar reconectar después de 3 segundos
          setTimeout(connectWebSocket, 3000)
        }
        
        ws.onerror = (error) => {
          console.error("Error WebSocket:", error)
          setIsConnected(false)
        }
        
      } catch (error) {
        console.error("Error conectando WebSocket:", error)
        setIsConnected(false)
      }
    }

    connectWebSocket()

    return () => {
      if (websocketRef.current) {
        websocketRef.current.close()
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  const parseErrors = (response: string) => {
    const errors: CodeError[] = []
    
    if (response.includes("Type checking passed")) {
      const lines = response.split("\n")
      
      for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim()
        if (line) {
          // Buscar patrones como "line 1:26 missing ';'"
          const match = line.match(/line (\d+):(\d+)\s+(.+)/)
          if (match) {
            const lineNum = parseInt(match[1])
            const colNum = parseInt(match[2])
            const message = match[3]
            
            errors.push({
              line: lineNum,
              column: colNum,
              message: message
            })
          }
        }
      }
    }
    
    setErrors(errors)
  }

  const sendToWebSocket = useCallback((content: string, extension: string) => {
    if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
      const message = `${extension}\n${content}`
      websocketRef.current.send(message)
    }
  }, [])

  const handleContentChange = (value: string) => {
    setLocalContent(value)
    if (activeFile) {
      onContentChange(activeFile, value)
      
      // Obtener la extensión del archivo
      const extension = activeFile.split(".").pop()?.toLowerCase() || "txt"
      
      // Cancelar timeout anterior
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
      
      // Enviar al WebSocket después de 500ms de inactividad
      timeoutRef.current = setTimeout(() => {
        sendToWebSocket(value, extension)
      }, 500)
    }
  }

  const handleSave = () => {
    if (activeFile) {
      console.log(`Saving ${activeFile}:`, localContent)
    }
  }

  const handleRun = () => {
    if (activeFile) {
      console.log(`Running ${activeFile}:`, localContent)
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(localContent)
  }

  const handleDownload = () => {
    if (activeFile) {
      const blob = new Blob([localContent], { type: "text/plain" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = activeFile.split("/").pop() || "file.txt"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  const getLanguage = (fileName: string) => {
    const ext = fileName.split(".").pop()?.toLowerCase()
    switch (ext) {
      case "js":
      case "jsx":
        return "javascript"
      case "ts":
      case "tsx":
        return "typescript"
      case "css":
        return "css"
      case "html":
        return "html"
      case "cps":
        return "compiScript"
      case "json":
        return "json"
      case "md":
        return "markdown"
      default:
        return "text"
    }
  }

  const highlightSyntax = (code: string, language: string) => {
    let highlighted = code

    if (language === "javascript" || language === "typescript") {
      highlighted = highlighted.replace(
        /\b(const|let|var|function|return|if|else|for|while|class|import|export|from|default|async|await|try|catch|finally)\b/g,
        '<span class="text-blue-400">$1</span>',
      )
      highlighted = highlighted.replace(
        /(["'`])((?:\\.|(?!\1)[^\\])*?)\1/g,
        '<span class="text-green-400">$1$2$1</span>',
      )
      highlighted = highlighted.replace(/\/\/.*$/gm, '<span class="text-gray-500">$&</span>')
      highlighted = highlighted.replace(/\/\*[\s\S]*?\*\//g, '<span class="text-gray-500">$&</span>')
    } else if (language === "css") {
      highlighted = highlighted.replace(/([a-zA-Z-]+)(\s*:)/g, '<span class="text-blue-400">$1</span>$2')
      highlighted = highlighted.replace(/(:\s*)([^;]+)(;?)/g, '$1<span class="text-green-400">$2</span>$3')
    } else if (language === "html") {
      highlighted = highlighted.replace(
        /(<\/?)([\w-]+)([^>]*>)/g,
        '<span class="text-red-400">$1</span><span class="text-blue-400">$2</span><span class="text-red-400">$3</span>',
      )
    }

    return highlighted
  }

  const syncScroll = () => {
    if (textareaRef.current && highlightRef.current) {
      highlightRef.current.scrollTop = textareaRef.current.scrollTop
      highlightRef.current.scrollLeft = textareaRef.current.scrollLeft
    }
  }

  const getErrorsForLine = (lineNumber: number) => {
    return errors.filter(error => error.line === lineNumber)
  }

  if (!activeFile) {
    return (
      <div className="flex-1 flex items-center justify-center bg-background">
        <div className="text-center text-muted-foreground">
          <div className="text-6xl mb-4">📝</div>
          <h3 className="text-lg font-medium mb-2">No file selected</h3>
          <p className="text-sm">Select a file from the explorer to start editing</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col bg-background">
      {/* Toolbar */}
      <div className="h-10 bg-card border-b border-border flex items-center px-3 gap-2">
        <Button variant="ghost" size="sm" onClick={handleSave} className="h-7 px-2">
          <Save className="h-3 w-3 mr-1" />
          Save
        </Button>
        <Button variant="ghost" size="sm" onClick={handleRun} className="h-7 px-2">
          <Play className="h-3 w-3 mr-1" />
          Run
        </Button>
        <Button variant="ghost" size="sm" onClick={handleCopy} className="h-7 px-2">
          <Copy className="h-3 w-3 mr-1" />
          Copy
        </Button>
        <Button variant="ghost" size="sm" onClick={handleDownload} className="h-7 px-2">
          <Download className="h-3 w-3 mr-1" />
          Download
        </Button>
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          <div className={cn(
            "w-2 h-2 rounded-full",
            isConnected ? "bg-green-500" : "bg-red-500"
          )} />
          <span className="text-xs text-muted-foreground">
            {isConnected ? "Connected" : "Disconnected"}
          </span>
          <span className="text-xs text-muted-foreground mx-2">•</span>
          <span className="text-xs text-muted-foreground">
            {getLanguage(activeFile)} • {localContent.split("\n").length} lines
            {errors.length > 0 && (
              <>
                <span className="mx-1">•</span>
                <span className="text-red-400">{errors.length} error{errors.length !== 1 ? 's' : ''}</span>
              </>
            )}
          </span>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Line numbers */}
        <div className="w-12 bg-muted border-r border-border flex flex-col text-xs text-muted-foreground font-mono">
          <div className="h-10 border-b border-border" />
          <div className="flex-1 py-2">
            {Array.from({ length: lineCount }, (_, i) => {
              const lineNumber = i + 1
              const lineErrors = getErrorsForLine(lineNumber)
              return (
                <div 
                  key={lineNumber} 
                  className={cn(
                    "h-5 px-2 text-right leading-5 relative",
                    lineErrors.length > 0 && "bg-red-500/20"
                  )}
                  title={lineErrors.map(e => e.message).join('; ')}
                >
                  {lineNumber}
                  {lineErrors.length > 0 && (
                    <div className="absolute left-0 top-0 w-1 h-full bg-red-500" />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Code editor container */}
        <div className="flex-1 relative">
          {/* Error highlights overlay */}
          <div className="absolute inset-0 p-4 font-mono text-sm leading-5 pointer-events-none overflow-auto whitespace-pre-wrap break-words">
            {errors.map((error, index) => {
              const lines = localContent.split('\n')
              const beforeLines = lines.slice(0, error.line - 1)
              const currentLine = lines[error.line - 1] || ''
              
              const beforeText = beforeLines.join('\n') + (beforeLines.length > 0 ? '\n' : '')
              const beforeColumn = currentLine.slice(0, error.column - 1)
              
              const topOffset = (beforeLines.length * 20) // 20px per line (5 * 4 for leading-5)
              const leftOffset = beforeColumn.length * 7.2 // Approximate character width
              
              return (
                <div
                  key={index}
                  className="absolute w-2 h-5 bg-red-500/50 border-b-2 border-red-500"
                  style={{
                    top: `${topOffset}px`,
                    left: `${leftOffset}px`,
                  }}
                  title={error.message}
                />
              )
            })}
          </div>

          {/* Syntax highlighting overlay */}
          <pre
            ref={highlightRef}
            className="absolute inset-0 p-4 font-mono text-sm leading-5 pointer-events-none overflow-auto whitespace-pre-wrap break-words"
            dangerouslySetInnerHTML={{
              __html: highlightSyntax(localContent, getLanguage(activeFile)),
            }}
          />

          {/* Actual textarea */}
          <textarea
            ref={textareaRef}
            value={localContent}
            onChange={(e) => handleContentChange(e.target.value)}
            onScroll={syncScroll}
            className={cn(
              "absolute inset-0 p-4 font-mono text-sm leading-5 resize-none outline-none",
              "bg-transparent text-transparent caret-foreground",
              "overflow-auto whitespace-pre-wrap break-words",
            )}
            style={{ caretColor: "white" }}
            spellCheck={false}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            data-gramm="false"
          />
        </div>
      </div>

      {/* Status bar */}
      <div className="h-8 bg-card border-t border-border flex items-center px-3 text-xs text-muted-foreground">
        <span>Ln {localContent.slice(0, textareaRef.current?.selectionStart || 0).split("\n").length}</span>
        <span className="mx-2">•</span>
        <span>
          Col{" "}
          {(textareaRef.current?.selectionStart || 0) -
            localContent.lastIndexOf("\n", (textareaRef.current?.selectionStart || 0) - 1)}
        </span>
        <div className="flex-1" />
        {errors.length > 0 && (
          <div className="flex items-center gap-2 text-red-400">
            <span>
              {errors.length} error{errors.length !== 1 ? 's' : ''} found
            </span>
            <div className="max-w-md truncate">
              {errors[0] && `Line ${errors[0].line}: ${errors[0].message}`}
            </div>
            <span className="mx-2">•</span>
          </div>
        )}
        <span>UTF-8</span>
      </div>
    </div>
  )
}