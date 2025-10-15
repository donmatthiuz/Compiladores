class LinkedScope:
    def __init__(self, id, parent=None, context_type="global", context_name=None):
        self.id = id
        self.parent = parent
        self.children = []
        self.symbols = {}
        
        # 🔥 NUEVO: Información de contexto
        self.context_type = context_type  # "global", "function", "block", "class", "if", "while", etc.
        self.context_name = context_name  # nombre de la función/clase si aplica
    
    def add_child(self, child):
        self.children.append(child)
    
    def add_symbol(self, name, type_):
        self.symbols[name] = type_
    
    def display(self, level=0):
        indent = "  " * level
        
        # 🔥 Mostrar contexto
        if self.context_name:
            header = f"{indent}Scope {self.id} [{self.context_type}: {self.context_name}]:\n"
        else:
            header = f"{indent}Scope {self.id} [{self.context_type}]:\n"
        
        s = header
        
        # Mostrar símbolos
        if self.symbols:
            for name, t in self.symbols.items():
                s += f"{indent}  {name}: {t}\n"
        else:
            s += f"{indent}  (vacío)\n"
        
        # Mostrar hijos
        for child in self.children:
            s += child.display(level + 1)
        
        return s


class LinkedTable:
    def __init__(self):
        self.root = LinkedScope(0, None, context_type="global")
        self.current = self.root
        self.counter = 1
    
    def enter_scope(self, context_type="block", context_name=None):
        """Crea un nuevo scope con contexto"""
        node = LinkedScope(self.counter, parent=self.current, 
                          context_type=context_type, context_name=context_name)
        self.current.add_child(node)
        self.current = node
        self.counter += 1
        return node
    
    def exit_scope(self):
        if self.current.parent:
            self.current = self.current.parent
    
    def add_symbol(self, name, type_):
        self.current.add_symbol(name, type_)
    
    def display(self):
        return self.root.display()