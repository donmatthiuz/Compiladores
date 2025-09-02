"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "./ui/button"
import { Save, Play, Copy, Download } from "lucide-react"
import { cn } from "@/lib/utils"

interface CodeEditorProps {
  activeFile: string | null
  content: string
  onContentChange: (filePath: string, content: string) => void
}

export function CodeEditor({ activeFile, content, onContentChange }: CodeEditorProps) {
  const [localContent, setLocalContent] = useState(content)
  const [lineCount, setLineCount] = useState(1)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const highlightRef = useRef<HTMLPreElement>(null)

  useEffect(() => {
    setLocalContent(content)
  }, [content])

  useEffect(() => {
    const lines = localContent.split("\n").length
    setLineCount(lines)
  }, [localContent])

  const handleContentChange = (value: string) => {
    setLocalContent(value)
    if (activeFile) {
      onContentChange(activeFile, value)
    }
  }

  const handleSave = () => {
    if (activeFile) {
      // In a real IDE, this would save to filesystem
      console.log(`Saving ${activeFile}:`, localContent)
    }
  }

  const handleRun = () => {
    if (activeFile) {
      // In a real IDE, this would execute the code
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
      case "json":
        return "json"
      case "md":
        return "markdown"
      default:
        return "text"
    }
  }

  const highlightSyntax = (code: string, language: string) => {
    // Basic syntax highlighting for common languages
    let highlighted = code

    if (language === "javascript" || language === "typescript") {
      // Keywords
      highlighted = highlighted.replace(
        /\b(const|let|var|function|return|if|else|for|while|class|import|export|from|default|async|await|try|catch|finally)\b/g,
        '<span class="text-blue-400">$1</span>',
      )
      // Strings
      highlighted = highlighted.replace(
        /(["'`])((?:\\.|(?!\1)[^\\])*?)\1/g,
        '<span class="text-green-400">$1$2$1</span>',
      )
      // Comments
      highlighted = highlighted.replace(/\/\/.*$/gm, '<span class="text-gray-500">$&</span>')
      highlighted = highlighted.replace(/\/\*[\s\S]*?\*\//g, '<span class="text-gray-500">$&</span>')
    } else if (language === "css") {
      // CSS properties
      highlighted = highlighted.replace(/([a-zA-Z-]+)(\s*:)/g, '<span class="text-blue-400">$1</span>$2')
      // CSS values
      highlighted = highlighted.replace(/(:\s*)([^;]+)(;?)/g, '$1<span class="text-green-400">$2</span>$3')
    } else if (language === "html") {
      // HTML tags
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
        <span className="text-xs text-muted-foreground">
          {getLanguage(activeFile)} • {localContent.split("\n").length} lines
        </span>
      </div>

      {/* Editor */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Line numbers */}
        <div className="w-12 bg-muted border-r border-border flex flex-col text-xs text-muted-foreground font-mono">
          <div className="h-10 border-b border-border" /> {/* Spacer for toolbar */}
          <div className="flex-1 py-2">
            {Array.from({ length: lineCount }, (_, i) => (
              <div key={i + 1} className="h-5 px-2 text-right leading-5">
                {i + 1}
              </div>
            ))}
          </div>
        </div>

        {/* Code editor container */}
        <div className="flex-1 relative">
          {/* Syntax highlighting overlay */}
          <pre
            ref={highlightRef}
            className="absolute inset-0 p-4 font-mono text-sm leading-5 pointer-events-none overflow-auto whitespace-pre-wrap break-words"
            style={{ color: "transparent" }}
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
      <div className="h-6 bg-card border-t border-border flex items-center px-3 text-xs text-muted-foreground">
        <span>Ln {localContent.slice(0, textareaRef.current?.selectionStart || 0).split("\n").length}</span>
        <span className="mx-2">•</span>
        <span>
          Col{" "}
          {(textareaRef.current?.selectionStart || 0) -
            localContent.lastIndexOf("\n", (textareaRef.current?.selectionStart || 0) - 1)}
        </span>
        <div className="flex-1" />
        <span>UTF-8</span>
      </div>
    </div>
  )
}
