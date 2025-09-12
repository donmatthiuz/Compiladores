"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { Button } from "./ui/button"
import { Save, Play, Copy, Download } from "lucide-react"
import { cn } from "@/lib/utils"

interface CodeError {
  line?: number
  column?: number
  message: string
  type: 'error' | 'warning' | 'info'
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
  const websocketRef = useRef<WebSocket | null>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    setLocalContent(content)
  }, [content])

  useEffect(() => {
    const lines = localContent.split("\n").length
    setLineCount(lines)
  }, [localContent])

  // Función para verificar si el archivo es .cps
  const isCompiScriptFile = (fileName: string | null) => {
    return fileName?.endsWith('.cps') || false
  }

  // Conectar al WebSocket solo para archivos .cps
  useEffect(() => {
    if (!isCompiScriptFile(activeFile)) {
      // Si no es un archivo .cps, desconectar WebSocket y limpiar errores
      if (websocketRef.current) {
        websocketRef.current.close()
        websocketRef.current = null
      }
      setIsConnected(false)
      setErrors([])
      return
    }

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
          // Intentar reconectar después de 3 segundos solo si el archivo sigue siendo .cps
          if (isCompiScriptFile(activeFile)) {
            setTimeout(connectWebSocket, 3000)
          }
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
  }, [activeFile]) // Dependencia en activeFile para reconectar cuando cambie

  const parseErrors = (response: string) => {
    // Solo parsear errores para archivos .cps
    if (!isCompiScriptFile(activeFile)) {
      return
    }

    const errors: CodeError[] = []
    
    // Ignorar mensajes del servidor WebSocket
    if (response.includes("Servidor WebSocket escuchando en")) {
      return
    }
    
    const lines = response.split("\n")
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue
      
      // Patrón 1: "line 1:26 missing ';'"
      const lineColMatch = line.match(/line (\d+):(\d+)\s+(.+)/)
      if (lineColMatch) {
        const lineNum = parseInt(lineColMatch[1])
        const colNum = parseInt(lineColMatch[2])
        const message = lineColMatch[3]
        
        errors.push({
          line: lineNum,
          column: colNum,
          message: message,
          type: 'error'
        })
        continue
      }
      
      // Patrón 2: "line 5 unexpected token"
      const lineOnlyMatch = line.match(/line (\d+)\s+(.+)/)
      if (lineOnlyMatch) {
        const lineNum = parseInt(lineOnlyMatch[1])
        const message = lineOnlyMatch[2]
        
        errors.push({
          line: lineNum,
          message: message,
          type: 'error'
        })
        continue
      }
      
      // Patrón 3: "Error: something went wrong"
      const errorMatch = line.match(/^(Error|Warning|Info):\s*(.+)/)
      if (errorMatch) {
        const type = errorMatch[1].toLowerCase() as 'error' | 'warning' | 'info'
        const message = errorMatch[2]
        
        errors.push({
          message: `${errorMatch[1]}: ${message}`,
          type: type
        })
        continue
      }
      
      // Patrón 4: Cualquier línea que contenga palabras clave de error
      const errorKeywords = ['error', 'failed', 'exception', 'invalid', 'unexpected', 'missing', 'undefined', 'null']
      const warningKeywords = ['warning', 'deprecated', 'caution']
      
      const lowerLine = line.toLowerCase()
      
      if (errorKeywords.some(keyword => lowerLine.includes(keyword))) {
        errors.push({
          message: line,
          type: 'error'
        })
        continue
      }
      
      if (warningKeywords.some(keyword => lowerLine.includes(keyword))) {
        errors.push({
          message: line,
          type: 'warning'
        })
        continue
      }
      
      // Patrón 5: Si no coincide con nada anterior pero no está vacío y no es un mensaje del servidor
      if (line.length > 0 && !line.includes("conectado") && !line.includes("servidor")) {
        errors.push({
          message: line,
          type: 'info'
        })
      }
    }
    
    setErrors(errors)
  }

  const sendToWebSocket = useCallback((content: string, extension: string) => {
    // Solo enviar al WebSocket para archivos .cps
    if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN && extension === 'cps') {
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
      
      // Solo procesar para archivos .cps
      if (extension === 'cps') {
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

  const getErrorsForLine = (lineNumber: number) => {
    return errors.filter(error => error.line === lineNumber)
  }

  const getErrorTypeColor = (type: 'error' | 'warning' | 'info') => {
    switch (type) {
      case 'error':
        return 'text-red-400'
      case 'warning':
        return 'text-yellow-400'
      case 'info':
        return 'text-blue-400'
      default:
        return 'text-red-400'
    }
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

  const errorCount = errors.filter(e => e.type === 'error').length
  const warningCount = errors.filter(e => e.type === 'warning').length
  const isCompiScript = isCompiScriptFile(activeFile)

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
          {isCompiScript && (
            <>
              <div className={cn(
                "w-2 h-2 rounded-full",
                isConnected ? "bg-green-500" : "bg-red-500"
              )} />
              <span className="text-xs text-muted-foreground">
                {isConnected ? "Connected" : "Disconnected"}
              </span>
              <span className="text-xs text-muted-foreground mx-2">•</span>
            </>
          )}
          <span className="text-xs text-muted-foreground">
            {getLanguage(activeFile)} • {localContent.split("\n").length} lines
            {errorCount > 0 && (
              <>
                <span className="mx-1">•</span>
                <span className="text-red-400">{errorCount} error{errorCount !== 1 ? 's' : ''}</span>
              </>
            )}
            {warningCount > 0 && (
              <>
                <span className="mx-1">•</span>
                <span className="text-yellow-400">{warningCount} warning{warningCount !== 1 ? 's' : ''}</span>
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
              const hasError = lineErrors.some(e => e.type === 'error')
              const hasWarning = lineErrors.some(e => e.type === 'warning')
              
              return (
                <div 
                  key={lineNumber} 
                  className={cn(
                    "h-5 px-2 text-right leading-5 relative",
                    hasError && "bg-red-500/20",
                    !hasError && hasWarning && "bg-yellow-500/20"
                  )}
                  title={lineErrors.map(e => e.message).join('; ')}
                >
                  {lineNumber}
                  {lineErrors.length > 0 && (
                    <div className={cn(
                      "absolute left-0 top-0 w-1 h-full",
                      hasError && "bg-red-500",
                      !hasError && hasWarning && "bg-yellow-500"
                    )} />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Code editor container */}
        <div className="flex-1 relative">
          {/* Error highlights overlay - solo para archivos .cps */}
          {isCompiScript && (
            <div className="absolute inset-0 p-4 font-mono text-sm leading-5 pointer-events-none overflow-auto whitespace-pre-wrap break-words">
              {errors.filter(error => error.line && error.column).map((error, index) => {
                const lines = localContent.split('\n')
                const beforeLines = lines.slice(0, (error.line || 1) - 1)
                const currentLine = lines[(error.line || 1) - 1] || ''
                
                const beforeColumn = currentLine.slice(0, (error.column || 1) - 1)
                
                const topOffset = (beforeLines.length * 20) // 20px per line (5 * 4 for leading-5)
                const leftOffset = beforeColumn.length * 7.2 // Approximate character width
                
                return (
                  <div
                    key={index}
                    className={cn(
                      "absolute w-2 h-5 border-b-2",
                      error.type === 'error' && "bg-red-500/50 border-red-500",
                      error.type === 'warning' && "bg-yellow-500/50 border-yellow-500",
                      error.type === 'info' && "bg-blue-500/50 border-blue-500"
                    )}
                    style={{
                      top: `${topOffset}px`,
                      left: `${leftOffset}px`,
                    }}
                    title={error.message}
                  />
                )
              })}
            </div>
          )}

          {/* Actual textarea */}
          <textarea
            ref={textareaRef}
            value={localContent}
            onChange={(e) => handleContentChange(e.target.value)}
            className={cn(
              "absolute inset-0 p-4 font-mono text-sm leading-5 resize-none outline-none",
              "bg-background text-foreground caret-foreground",
              "overflow-auto whitespace-pre-wrap break-words",
            )}
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
        {errors.length > 0 && isCompiScript && (
          <div className="flex items-center gap-2">
            {errorCount > 0 && (
              <span className="text-red-400">
                {errorCount} error{errorCount !== 1 ? 's' : ''}
              </span>
            )}
            {warningCount > 0 && (
              <>
                {errorCount > 0 && <span className="mx-1">•</span>}
                <span className="text-yellow-400">
                  {warningCount} warning{warningCount !== 1 ? 's' : ''}
                </span>
              </>
            )}
            {errors[0] && (
              <>
                <span className="mx-2">•</span>
                <div className={cn("max-w-md truncate", getErrorTypeColor(errors[0].type))}>
                  {errors[0].line ? `Line ${errors[0].line}: ` : ''}{errors[0].message}
                </div>
              </>
            )}
            <span className="mx-2">•</span>
          </div>
        )}
        <span>UTF-8</span>
      </div>
    </div>
  )
}