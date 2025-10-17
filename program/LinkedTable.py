class LinkedScope:
    """
    Nodo de la tabla enlazada de scopes. Guarda:
      - id del scope
      - relación padre/hijos
      - símbolos {nombre -> tipo}
      - offsets relativos {nombre -> offset}  (opcional)
      - metadatos de contexto (tipo de contexto y nombre)
    """
    def __init__(self, id, parent=None, context_type="global", context_name=None):
        self.id = id
        self.parent = parent
        self.children = []
        self.symbols = {}
        self.offsets = {}  # nombre -> offset relativo (int)
        # Metadatos de contexto
        self.context_type = context_type  # "global", "function", "block", "class", "if", "while"
        self.context_name = context_name  # nombre de la función/clase si aplica

    # --------------------------
    # Mutadores
    # --------------------------
    def add_child(self, child: "LinkedScope"):
        self.children.append(child)

    def add_symbol(self, name, type_, offset=None):
        """Registra un símbolo en este scope. 'type_' puede ser una cadena o un objeto Type."""
        self.symbols[name] = type_
        if offset is not None:
            self.offsets[name] = offset

    def update_offset(self, name, new_offset):
        """Actualiza/crea el offset relativo de un símbolo de este scope."""
        self.offsets[name] = new_offset

    # --------------------------
    # Acceso
    # --------------------------
    def get_offset(self, name, default=None):
        return self.offsets.get(name, default)

    def has_symbol(self, name):
        return name in self.symbols

    # --------------------------
    # Render
    # --------------------------
    def _header_line(self, indent=""):
        ctx = self.context_type if self.context_type else "?"
        nm = f" {self.context_name}" if self.context_name else ""
        parent_id = self.parent.id if self.parent else None
        return f"{indent}Scope#{self.id}<{ctx}{nm}> parent={parent_id}\n"

    def display(self, indent=""):
        """Devuelve un string con todo el subárbol a partir de este nodo."""
        s = self._header_line(indent)

        if self.symbols:
            for name, t in self.symbols.items():
                off = self.offsets.get(name, None)
                off_str = f" @off={off}" if off is not None else ""
                s += f"{indent}  {name}: {t}{off_str}\n"
        else:
            s += f"{indent}  (vacío)\n"

        for ch in self.children:
            s += ch.display(indent + "  ")
        return s


class LinkedTable:
    """
    Tabla enlazada de scopes para navegación y depuración durante type-check y codegen.
    """
    def __init__(self):
        self.root = LinkedScope(0, None, context_type="global")
        self.current = self.root
        self.counter = 1

    # --------------------------
    # Scopes
    # --------------------------
    def enter_scope(self, context_type="block", context_name=None):
        """
        Crea un scope hijo del scope actual y lo activa.
        Devuelve el nodo creado.
        """
        node = LinkedScope(self.counter, self.current,
                           context_type=context_type, context_name=context_name)
        self.current.add_child(node)
        self.current = node
        self.counter += 1
        return node

    def exit_scope(self):
        """Vuelve al scope padre (si existe)."""
        if self.current.parent:
            self.current = self.current.parent

    # --------------------------
    # Símbolos / Offsets
    # --------------------------
    def add_symbol(self, name, type_, offset=None):
        self.current.add_symbol(name, type_, offset)

    def update_offset(self, scope_id, name, new_offset):
        """
        Actualiza el offset de 'name' en el scope cuyo id es 'scope_id'.
        No sube/baja en la jerarquía: la actualización es local a ese scope.
        """
        node = self._find_by_id(self.root, scope_id)
        if node:
            node.update_offset(name, new_offset)

    def get_offset(self, scope_id, name, default=None):
        node = self._find_by_id(self.root, scope_id)
        if not node:
            return default
        return node.get_offset(name, default)

    # --------------------------
    # Búsquedas / utilidades
    # --------------------------
    def _find_by_id(self, node: LinkedScope, target_id: int):
        if node.id == target_id:
            return node
        for ch in node.children:
            r = self._find_by_id(ch, target_id)
            if r:
                return r
        return None

    def resolve_in_scopes(self, name):
        """
        Busca 'name' en el scope actual y sube hasta la raíz.
        Devuelve (scope_node, type, offset) o (None, None, None) si no se encuentra.
        """
        node = self.current
        while node is not None:
            if node.has_symbol(name):
                return node, node.symbols[name], node.get_offset(name)
            node = node.parent
        return None, None, None

    # --------------------------
    # Render
    # --------------------------
    def display(self):
        return self.root.display()
    
    def save_to_file(self, filename="linked_table.txt"):

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.display())
            print(f"✅ Tabla enlazada guardada en: {filename}")
        except Exception as e:
            print(f"⚠️ Error al guardar la tabla enlazada: {e}")
