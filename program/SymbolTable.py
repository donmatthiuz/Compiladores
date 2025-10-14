class Symbol:
    def __init__(self, name, type_, scope_level, offset=None):
        self.name = name
        self.type_ = type_
        self.scope_level = scope_level
        self.offset = offset  # posición relativa de memoria

    def set_offset(self, new_offset):
        """Permite actualizar el offset después de la definición"""
        self.offset = new_offset

    def __repr__(self):
        off_str = f", offset={self.offset}" if self.offset is not None else ""
        return f"{self.name}:{self.type_} (scope {self.scope_level}{off_str})"


class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent
        self.scope_level = 0 if parent is None else parent.scope_level + 1
        self.next_offset = 0  # contador para asignar offsets automáticos
     
    def define(self, name, type_):
        if name in self.symbols:
            raise Exception(f"Error: '{name}' ya definido en este ámbito.")
        # crear símbolo con offset automático
        symbol = Symbol(name, type_, self.scope_level, offset=self.next_offset)
        self.symbols[name] = symbol
        self.next_offset += 4  # simula tamaño de variable (4 bytes)
        return symbol
     
    def lookup(self, name):
        """Busca un símbolo en este ámbito y en los ámbitos padre"""
        if name in self.symbols:
            return self.symbols[name]
        elif self.parent:
            return self.parent.lookup(name)
        else:
            return None
    
    def lookup_current_scope(self, name):
        """Busca un símbolo SOLO en el ámbito actual (no en los padre)"""
        return self.symbols.get(name, None)
    
    def update_offset(self, name, new_offset):
        """Actualiza el offset de un símbolo ya definido"""
        symbol = self.lookup(name)
        if symbol:
            symbol.set_offset(new_offset)
        else:
            raise Exception(f"No se encontró el símbolo '{name}' para actualizar offset.")
     
    def __repr__(self):
        return f"Scope {self.scope_level}: {list(self.symbols.values())}"
