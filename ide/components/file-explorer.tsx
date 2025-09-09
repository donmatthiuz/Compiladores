"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import {
  File,
  Folder,
  FolderOpen,
  Plus,
  FileText,
  Code,
  ImageIcon,
  Settings,

  Trash2,
  Edit3,
  FolderPlus,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface FileNode {
  name: string
  type: "file" | "folder"
  path: string
  children?: FileNode[]
  expanded?: boolean
}

interface FileExplorerProps {
  onFileSelect: (filePath: string) => void
  activeFile: string | null
}

interface ContextMenu {
  x: number
  y: number
  node: FileNode | null
  visible: boolean
}

export function FileExplorer({ onFileSelect, activeFile }: FileExplorerProps) {
  const [files, setFiles] = useState<FileNode[]>([
    {
      name: "src",
      type: "folder",
      path: "src",
      expanded: true,
      children: [
        { name: "index.js", type: "file", path: "src/index.js" },
        { name: "app.js", type: "file", path: "src/app.js" },
        { name: "styles.css", type: "file", path: "src/styles.css" },
      ],
    },
    {
      name: "public",
      type: "folder",
      path: "public",
      children: [
        { name: "index.html", type: "file", path: "public/index.html" },
        { name: "favicon.ico", type: "file", path: "public/favicon.ico" },
      ],
    },
    { name: "package.json", type: "file", path: "package.json" },
    { name: "README.md", type: "file", path: "README.md" },
  ])

  const [newFileName, setNewFileName] = useState("")
  const [showNewFileInput, setShowNewFileInput] = useState(false)
  const [showNewFolderInput, setShowNewFolderInput] = useState(false)
  const [contextMenu, setContextMenu] = useState<ContextMenu>({ x: 0, y: 0, node: null, visible: false })
  const [renamingNode, setRenamingNode] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState("")
  const contextMenuRef = useRef<HTMLDivElement>(null)

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split(".").pop()?.toLowerCase()
    switch (ext) {
      case "js":
      case "jsx":
      case "ts":
      case "tsx":
        return <Code className="h-4 w-4 text-yellow-400" />
      case "css":
      case "scss":
        return <FileText className="h-4 w-4 text-blue-400" />
      case "html":
        return <FileText className="h-4 w-4 text-orange-400" />
      case "json":
        return <Settings className="h-4 w-4 text-green-400" />
      case "cps":
        return <Code className="h-4 w-4 text-red-400" />
      case "md":
        return <FileText className="h-4 w-4 text-gray-400" />
      case "png":
      case "jpg":
      case "jpeg":
      case "gif":
        return <ImageIcon className="h-4 w-4 text-purple-400" />
      default:
        return <File className="h-4 w-4 text-muted-foreground" />
    }
  }

  const toggleFolder = (path: string) => {
    const updateNode = (nodes: FileNode[]): FileNode[] => {
      return nodes.map((node) => {
        if (node.path === path && node.type === "folder") {
          return { ...node, expanded: !node.expanded }
        }
        if (node.children) {
          return { ...node, children: updateNode(node.children) }
        }
        return node
      })
    }
    setFiles(updateNode(files))
  }

  const addNewFile = (isFolder = false) => {
    if (!newFileName.trim()) return

    const newNode: FileNode = {
      name: newFileName,
      type: isFolder ? "folder" : "file",
      path: newFileName,
      children: isFolder ? [] : undefined,
      expanded: isFolder ? false : undefined,
    }

    setFiles((prev) => [...prev, newNode])
    setNewFileName("")
    setShowNewFileInput(false)
    setShowNewFolderInput(false)

    if (!isFolder) {
      onFileSelect(newFileName)
    }
  }

  const deleteNode = (pathToDelete: string) => {
    const removeNode = (nodes: FileNode[]): FileNode[] => {
      return nodes.filter((node) => {
        if (node.path === pathToDelete) {
          return false
        }
        if (node.children) {
          node.children = removeNode(node.children)
        }
        return true
      })
    }
    setFiles(removeNode(files))

    // Clear active file if it was deleted
    if (activeFile === pathToDelete) {
      onFileSelect("")
    }
  }

  const startRename = (node: FileNode) => {
    setRenamingNode(node.path)
    setRenameValue(node.name)
  }

  const finishRename = () => {
    if (!renamingNode || !renameValue.trim()) {
      setRenamingNode(null)
      setRenameValue("")
      return
    }

    const updateNode = (nodes: FileNode[]): FileNode[] => {
      return nodes.map((node) => {
        if (node.path === renamingNode) {
          const newPath = node.path.replace(node.name, renameValue.trim())
          return { ...node, name: renameValue.trim(), path: newPath }
        }
        if (node.children) {
          return { ...node, children: updateNode(node.children) }
        }
        return node
      })
    }

    setFiles(updateNode(files))
    setRenamingNode(null)
    setRenameValue("")
  }

  const handleContextMenu = (e: React.MouseEvent, node: FileNode) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      node,
      visible: true,
    })
  }

  const hideContextMenu = () => {
    setContextMenu({ x: 0, y: 0, node: null, visible: false })
  }

  const renderFileTree = (nodes: FileNode[], depth = 0) => {
    return nodes.map((node) => (
      <div key={node.path}>
        <div
          className={cn(
            "flex items-center gap-2 px-2 py-1 hover:bg-accent/50 cursor-pointer text-sm group",
            activeFile === node.path && "bg-accent text-accent-foreground",
            `ml-${depth * 4}`,
          )}
          onClick={() => {
            if (node.type === "folder") {
              toggleFolder(node.path)
            } else {
              onFileSelect(node.path)
            }
          }}
          onContextMenu={(e) => handleContextMenu(e, node)}
        >
          {node.type === "folder" ? (
            node.expanded ? (
              <FolderOpen className="h-4 w-4 text-blue-400" />
            ) : (
              <Folder className="h-4 w-4 text-blue-400" />
            )
          ) : (
            getFileIcon(node.name)
          )}

          {renamingNode === node.path ? (
            <Input
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") finishRename()
                if (e.key === "Escape") {
                  setRenamingNode(null)
                  setRenameValue("")
                }
              }}
              onBlur={finishRename}
              className="h-5 text-xs flex-1"
              autoFocus
            />
          ) : (
            <span className="truncate flex-1">{node.name}</span>
          )}
        </div>
        {node.type === "folder" && node.expanded && node.children && (
          <div>{renderFileTree(node.children, depth + 1)}</div>
        )}
      </div>
    ))
  }

  return (
    <div className="flex-1 flex flex-col" onClick={hideContextMenu}>
      {/* File tree */}
      <div className="flex-1 overflow-auto p-2">
        {renderFileTree(files)}

        {/* New file input */}
        {showNewFileInput && (
          <div className="flex items-center gap-2 px-2 py-1">
            <File className="h-4 w-4 text-muted-foreground" />
            <Input
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") addNewFile(false)
                if (e.key === "Escape") {
                  setShowNewFileInput(false)
                  setNewFileName("")
                }
              }}
              placeholder="filename.ext"
              className="h-6 text-xs"
              autoFocus
            />
          </div>
        )}

        {/* New folder input */}
        {showNewFolderInput && (
          <div className="flex items-center gap-2 px-2 py-1">
            <Folder className="h-4 w-4 text-blue-400" />
            <Input
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") addNewFile(true)
                if (e.key === "Escape") {
                  setShowNewFolderInput(false)
                  setNewFileName("")
                }
              }}
              placeholder="folder name"
              className="h-6 text-xs"
              autoFocus
            />
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="border-t border-border p-2 space-y-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowNewFileInput(true)}
          className="w-full justify-start gap-2 h-8"
        >
          <Plus className="h-4 w-4" />
          New File
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowNewFolderInput(true)}
          className="w-full justify-start gap-2 h-8"
        >
          <FolderPlus className="h-4 w-4" />
          New Folder
        </Button>
      </div>

      {/* Context Menu */}
      {contextMenu.visible && contextMenu.node && (
        <div
          ref={contextMenuRef}
          className="fixed bg-popover border border-border rounded-md shadow-lg py-1 z-50 min-w-32"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className="w-full px-3 py-1 text-left text-sm hover:bg-accent hover:text-accent-foreground flex items-center gap-2"
            onClick={() => {
              startRename(contextMenu.node!)
              hideContextMenu()
            }}
          >
            <Edit3 className="h-3 w-3" />
            Rename
          </button>
          <button
            className="w-full px-3 py-1 text-left text-sm hover:bg-destructive hover:text-destructive-foreground flex items-center gap-2"
            onClick={() => {
              deleteNode(contextMenu.node!.path)
              hideContextMenu()
            }}
          >
            <Trash2 className="h-3 w-3" />
            Delete
          </button>
        </div>
      )}
    </div>
  )
}
