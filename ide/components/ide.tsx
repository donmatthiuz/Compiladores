"use client"

import { useState } from "react"
import { FileExplorer } from "./file-explorer"
import { CodeEditor } from "./code-editor"
import { Terminal } from "./terminal"
import { Button } from "./ui/button"
import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from "lucide-react"

export function IDE() {
  const [leftPanelOpen, setLeftPanelOpen] = useState(true)
  const [rightPanelOpen, setRightPanelOpen] = useState(true)
  const [activeFile, setActiveFile] = useState<string | null>(null)
  const [fileContents, setFileContents] = useState<Record<string, string>>({})

  const handleFileSelect = (filePath: string) => {
    setActiveFile(filePath)
    // Initialize file content if not exists
    if (!fileContents[filePath]) {
      setFileContents((prev) => ({
        ...prev,
        [filePath]: `// ${filePath}\n// Start coding here...`,
      }))
    }
  }

  const handleFileContentChange = (filePath: string, content: string) => {
    setFileContents((prev) => ({
      ...prev,
      [filePath]: content,
    }))
  }

  // Nueva función para manejar el contenido de archivos cargados
  const handleFileContent = (filePath: string, content: string) => {
    setFileContents((prev) => ({
      ...prev,
      [filePath]: content,
    }))
  }

  return (
    <div className="h-screen flex flex-col bg-background text-foreground">
      {/* Header */}
      <header className="h-12 bg-card border-b border-border flex items-center px-4 gap-2">
        <Button variant="ghost" size="sm" onClick={() => setLeftPanelOpen(!leftPanelOpen)} className="h-8 w-8 p-0">
          {leftPanelOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
        </Button>
        <h1 className="text-lg font-semibold">IDE</h1>
        <div className="flex-1" />
        <Button variant="ghost" size="sm" onClick={() => setRightPanelOpen(!rightPanelOpen)} className="h-8 w-8 p-0">
          {rightPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
        </Button>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* File Explorer Panel */}
        {leftPanelOpen && (
          <div className="w-64 bg-card border-r border-border flex flex-col">
            <div className="h-10 bg-muted border-b border-border flex items-center px-3">
              <span className="text-sm font-medium">Explorer</span>
            </div>
            <FileExplorer 
              onFileSelect={handleFileSelect} 
              activeFile={activeFile}
              onFileContent={handleFileContent}
            />
          </div>
        )}

        {/* Code Editor Panel */}
        <div className="flex-1 flex flex-col">
          <div className="h-10 bg-muted border-b border-border flex items-center px-3">
            <span className="text-sm font-medium">{activeFile ? activeFile : "No file selected"}</span>
          </div>
          <CodeEditor
            activeFile={activeFile}
            content={activeFile ? fileContents[activeFile] || "" : ""}
            onContentChange={handleFileContentChange}
          />
        </div>

        {/* Terminal Panel */}
        {rightPanelOpen && (
          <div className="w-80 bg-card border-l border-border flex flex-col">
            <div className="h-10 bg-muted border-b border-border flex items-center px-3">
              <span className="text-sm font-medium">Terminal</span>
            </div>
            <Terminal />
          </div>
        )}
      </div>
    </div>
  )
}