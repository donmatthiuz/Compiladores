"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Save, Play, Copy, Download, ChevronUp, ChevronDown, X, AlertCircle, AlertTriangle, Info } from "lucide-react"
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
  const [showErrorPanel, setShowErrorPanel] = useState(false)
  const [errorPanelHeight, setErrorPanelHeight] = useState(200)
  const [selectedError, setSelectedError] = useState<number | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const websocketRef = useRef<WebSocket | null>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)
  const resizeRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setLocalContent(content)
  }, [content])

  useEffect(() => {
    const lines = localContent.split("\n").length
    setLineCount(lines)
  }, [localContent])

  // Auto-mostrar panel cuando hay errores
  useEffect(() => {
    if (errors.length > 0 && isCompiScriptFile(activeFile)) {
      setShowErrorPanel(true)
    } else if (errors.length === 0) {
      setShowErrorPanel(false)
    }
  }, [errors.length])

  // Función para verificar si el archivo es .cps
  const isCompiScriptFile = (fileName: string | null) => {
    return fileName?.endsWith('.cps') || false
  }

  // Conectar al WebSocket solo para archivos .cps
  useEffect(() => {
    if (!isCompiScriptFile(activeFile)) {
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
  }, [activeFile])

  const parseErrors = (response: string) => {
    if (!isCompiScriptFile(activeFile)) {
      return
    }

    const errors: CodeError[] = []
    
    if (response.includes("Servidor WebSocket escuchando en")) {
      return
    }
    
    const lines = response.split("\n")
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue
      
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
    if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN && extension === 'cps') {
      const message = `${extension}\n${content}`
      websocketRef.current.send(message)
    }
  }, [])

  const handleContentChange = (value: string) => {
    setLocalContent(value)
    if (activeFile) {
      onContentChange(activeFile, value)
      
      const extension = activeFile.split(".").pop()?.toLowerCase() || "txt"
      
      if (extension === 'cps') {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current)
        }
        
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
    if (activeFile && isCompiScriptFile(activeFile)) {
      const extension = activeFile.split(".").pop()?.toLowerCase() || "cps"
      const message = `${extension}|runner\n${localContent}`
      if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
        websocketRef.current.send(message)
      }
      console.log(message)
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

  const getErrorIcon = (type: 'error' | 'warning' | 'info') => {
    switch (type) {
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case 'info':
        return <Info className="h-4 w-4 text-blue-500" />
    }
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

  const goToError = (error: CodeError, index: number) => {
    setSelectedError(index)
    if (error.line && textareaRef.current) {
      const lines = localContent.split('\n')
      let position = 0
      for (let i = 0; i < error.line - 1; i++) {
        position += lines[i].length + 1
      }
      if (error.column) {
        position += error.column - 1
      }
      textareaRef.current.focus()
      textareaRef.current.setSelectionRange(position, position)
      textareaRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  // Manejo del resize del panel de errores
  useEffect(() => {
    const resizeElement = resizeRef.current
    if (!resizeElement) return

    let startY = 0
    let startHeight = 0

    const handleMouseDown = (e: MouseEvent) => {
      startY = e.clientY
      startHeight = errorPanelHeight
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      e.preventDefault()
    }

    const handleMouseMove = (e: MouseEvent) => {
      const delta = startY - e.clientY
      const newHeight = Math.max(100, Math.min(500, startHeight + delta))
      setErrorPanelHeight(newHeight)
    }

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    resizeElement.addEventListener('mousedown', handleMouseDown)

    return () => {
      resizeElement.removeEventListener('mousedown', handleMouseDown)
    }
  }, [errorPanelHeight])

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
  const infoCount = errors.filter(e => e.type === 'info').length
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

      {/* Editor Container */}
      <div className="flex-1 flex flex-col relative overflow-hidden">
        {/* Editor */}
        <div 
          className="flex relative overflow-hidden"
          style={{ height: showErrorPanel ? `calc(100% - ${errorPanelHeight}px)` : '100%' }}
        >
          {/* Line numbers */}
          <div className="w-12 bg-muted border-r border-border flex flex-col text-xs text-muted-foreground font-mono">
            <div className="h-10 border-b border-border" />
            <div className="flex-1 py-2 overflow-hidden">
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
            {/* Error highlights overlay */}
            {isCompiScript && (
              <div className="absolute inset-0 p-4 font-mono text-sm leading-5 pointer-events-none overflow-auto whitespace-pre-wrap break-words">
                {errors.filter(error => error.line && error.column).map((error, index) => {
                  const lines = localContent.split('\n')
                  const lineIndex = (error.line || 1) - 1
                  const beforeLines = lines.slice(0, lineIndex)
                  const currentLine = lines[lineIndex] || ''
                  
                  const beforeColumn = currentLine.slice(0, (error.column || 1) - 1)
                  
                  // Calcular el offset vertical: cada línea ocupa 1.25rem (20px con leading-5)
                  const topOffset = lineIndex * 20 + 16 // 16px es el padding-top
                  // Calcular el offset horizontal: aproximadamente 0.6em por carácter en fuente monospace
                  const leftOffset = beforeColumn.length * 8.4 + 16 // 16px es el padding-left
                  
                  return (
                    <div
                      key={index}
                      className={cn(
                        "absolute h-5 border-b-2",
                        error.type === 'error' && "bg-red-500/50 border-red-500",
                        error.type === 'warning' && "bg-yellow-500/50 border-yellow-500",
                        error.type === 'info' && "bg-blue-500/50 border-blue-500"
                      )}
                      style={{
                        top: `${topOffset}px`,
                        left: `${leftOffset}px`,
                        width: '8px',
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

        {/* Error Panel */}
        {showErrorPanel && isCompiScript && (
          <div 
            className="border-t border-border flex flex-col bg-card"
            style={{ height: `${errorPanelHeight}px` }}
          >
            {/* Resize handle */}
            <div
              ref={resizeRef}
              className="h-1 w-full bg-border hover:bg-primary cursor-ns-resize transition-colors"
            />

            {/* Panel header */}
            <div className="h-8 border-b border-border flex items-center px-3 gap-2">
              <div className="flex items-center gap-3 text-xs">
                <span className="font-medium">Problems</span>
                {errorCount > 0 && (
                  <div className="flex items-center gap-1">
                    <AlertCircle className="h-3 w-3 text-red-500" />
                    <span className="text-red-400">{errorCount}</span>
                  </div>
                )}
                {warningCount > 0 && (
                  <div className="flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3 text-yellow-500" />
                    <span className="text-yellow-400">{warningCount}</span>
                  </div>
                )}
                {infoCount > 0 && (
                  <div className="flex items-center gap-1">
                    <Info className="h-3 w-3 text-blue-500" />
                    <span className="text-blue-400">{infoCount}</span>
                  </div>
                )}
              </div>
              <div className="flex-1" />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowErrorPanel(false)}
                className="h-6 w-6 p-0"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>

            {/* Error list */}
            <div className="flex-1 overflow-auto">
              {errors.length === 0 ? (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  No problems detected
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {errors.map((error, index) => (
                    <div
                      key={index}
                      onClick={() => goToError(error, index)}
                      className={cn(
                        "px-4 py-2 hover:bg-muted/50 cursor-pointer transition-colors",
                        selectedError === index && "bg-muted"
                      )}
                    >
                      <div className="flex items-start gap-2">
                        <div className="mt-0.5">
                          {getErrorIcon(error.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-foreground break-words">
                            {error.message}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                            <span>{activeFile}</span>
                            {error.line && (
                              <>
                                <span>•</span>
                                <span>Line {error.line}</span>
                                {error.column && (
                                  <>
                                    <span>•</span>
                                    <span>Col {error.column}</span>
                                  </>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
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
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowErrorPanel(!showErrorPanel)}
            className="h-6 px-2 gap-1"
          >
            {getErrorIcon(errors[0].type)}
            <span className={getErrorTypeColor(errors[0].type)}>
              {errorCount} error{errorCount !== 1 ? 's' : ''}
              {warningCount > 0 && `, ${warningCount} warning${warningCount !== 1 ? 's' : ''}`}
            </span>
            {showErrorPanel ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />}
          </Button>
        )}
        <span className="mx-2">•</span>
        <span>UTF-8</span>
      </div>
    </div>
  )
}