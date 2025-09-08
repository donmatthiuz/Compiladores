class Type:
    pass

class IntType(Type):
    def __str__(self):
        return "integer"

class FloatType(Type):
    def __str__(self):
        return "float"

class StringType(Type):
    def __str__(self):
        return "string"

class BoolType(Type):
    def __str__(self):
        return "boolean"

class NullType(Type):
    def __str__(self):
        return "null"

class ArrayType(Type):
    def __init__(self, element_type: Type, dimensions: int = 1):
        self.element_type = element_type
        self.dimensions = dimensions

    def __str__(self):
        return f"{self.element_type}{'[]' * self.dimensions}"

class ClassType(Type):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

class FunctionType(Type):
    def __init__(self, param_types, return_type: Type):
        self.param_types = param_types  # list of Type
        self.return_type = return_type

    def __str__(self):
        params = ", ".join(str(p) for p in self.param_types)
        return f"function({params}): {self.return_type}"
