class Symbol:
    def __init__(self, name, type_, scope_level):
        self.name = name
        self.type_ = type_
        self.scope_level = scope_level

    def __repr__(self):
        return f"{self.name}:{self.type_} (scope {self.scope_level})"


class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent
        self.scope_level = 0 if parent is None else parent.scope_level + 1

    def define(self, name, type_):
        if name in self.symbols:
            raise Exception(f"Error: '{name}' ya definido en este ámbito.")
        self.symbols[name] = Symbol(name, type_, self.scope_level)

    def lookup(self, name):
        if name in self.symbols:
            return self.symbols[name]
        elif self.parent:
            return self.parent.lookup(name)
        else:
            return None

    def __repr__(self):
        return f"Scope {self.scope_level}: {list(self.symbols.values())}"



