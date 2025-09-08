from CompiScriptParser import CompiScriptParser
from CompiScriptVisitor import CompiScriptVisitor
from custom_types import IntType, FloatType, StringType, BoolType, NullType, ArrayType, ClassType, FunctionType
from SymbolTable import SymbolTable

class TypeCheckVisitor(CompiScriptVisitor):
    def __init__(self):
        self.symbol_table = SymbolTable()  # Tabla de símbolos global
        self.current_scope = self.symbol_table
        
    def enter_scope(self):
        """Entra a un nuevo ámbito"""
        new_scope = SymbolTable(parent=self.current_scope)
        self.current_scope = new_scope
        return new_scope
    
    def exit_scope(self):
        """Sale del ámbito actual"""
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent
    
    # =====================================
    # EXPRESIONES ARITMÉTICAS
    # =====================================
    
    def visitMultiplicativeExpr(self, ctx: CompiScriptParser.MultiplicativeExprContext):
        """Maneja *, /, %"""
        if len(ctx.unaryExpr()) == 1:
            # Solo hay un término, no es operación binaria
            return self.visit(ctx.unaryExpr(0))
        
        # Procesar operaciones de izquierda a derecha
        result_type = self.visit(ctx.unaryExpr(0))
        
        for i in range(1, len(ctx.unaryExpr())):
            operator = ctx.getChild(2*i-1).getText()  # *, /, %
            right_type = self.visit(ctx.unaryExpr(i))
            
            if operator in ['*', '/']:
                result_type = self._check_arithmetic_operation(result_type, right_type, operator)
            elif operator == '%':
                result_type = self._check_modulo_operation(result_type, right_type)
        
        return result_type
    
    def visitAdditiveExpr(self, ctx: CompiScriptParser.AdditiveExprContext):
        """Maneja +, -"""
        if len(ctx.multiplicativeExpr()) == 1:
            # Solo hay un término, no es operación binaria
            return self.visit(ctx.multiplicativeExpr(0))
        
        # Procesar operaciones de izquierda a derecha
        result_type = self.visit(ctx.multiplicativeExpr(0))
        
        for i in range(1, len(ctx.multiplicativeExpr())):
            operator = ctx.getChild(2*i-1).getText()  # +, -
            right_type = self.visit(ctx.multiplicativeExpr(i))
            
            if operator == '+':
                result_type = self._check_addition_operation(result_type, right_type)
            elif operator == '-':
                result_type = self._check_subtraction_operation(result_type, right_type)
        
        return result_type
    
    def visitUnaryExpr(self, ctx: CompiScriptParser.UnaryExprContext):
        """Maneja operadores unarios -, !"""
        if ctx.getChildCount() == 1:
            # No hay operador unario
            return self.visit(ctx.primaryExpr())
        
        operator = ctx.getChild(0).getText()  # - o !
        operand_type = self.visit(ctx.unaryExpr())
        
        if operator == '-':
            if isinstance(operand_type, (IntType, FloatType)):
                return operand_type
            else:
                raise TypeError(f"Operador unario '-' no soportado para tipo: {operand_type}")
        elif operator == '!':
            if isinstance(operand_type, BoolType):
                return BoolType()
            else:
                raise TypeError(f"Operador unario '!' no soportado para tipo: {operand_type}")
    
    # =====================================
    # LITERALES
    # =====================================
    
    def visitLiteralExpr(self, ctx: CompiScriptParser.LiteralExprContext):
        """Maneja literales"""
        if ctx.Literal():
            literal_text = ctx.Literal().getText()
            if literal_text.startswith('"') and literal_text.endswith('"'):
                return StringType()
            elif literal_text.isdigit():
                return IntType()
        elif ctx.getText() == 'true' or ctx.getText() == 'false':
            return BoolType()
        elif ctx.getText() == 'null':
            return NullType()
        
        return None
    
    def visitIdentifierExpr(self, ctx: CompiScriptParser.IdentifierExprContext):
        """Maneja identificadores"""
        name = ctx.Identifier().getText()
        symbol = self.current_scope.lookup(name)
        
        if symbol is None:
            raise NameError(f"Variable '{name}' no definida")
        
        return symbol.type_
    
    def visitPrimaryExpr(self, ctx: CompiScriptParser.PrimaryExprContext):
        """Maneja expresiones primarias"""
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        elif ctx.leftHandSide():
            return self.visit(ctx.leftHandSide())
        elif ctx.expression():
            # Expresión entre paréntesis
            return self.visit(ctx.expression())
        
        return None
    
    def visitLeftHandSide(self, ctx: CompiScriptParser.LeftHandSideContext):
        """Maneja lado izquierdo de asignaciones"""
        base_type = self.visit(ctx.primaryAtom())
        
        # Procesar operaciones de sufijo (llamadas, indexación, acceso a propiedades)
        current_type = base_type
        for suffix in ctx.suffixOp():
            current_type = self._process_suffix_operation(current_type, suffix)
        
        return current_type
    
    # =====================================
    # MÉTODOS AUXILIARES PARA VERIFICACIÓN DE TIPOS
    # =====================================
    
    def _check_arithmetic_operation(self, left_type, right_type, operator):
        """Verifica operaciones aritméticas *, /"""
        if isinstance(left_type, (IntType, FloatType)) and isinstance(right_type, (IntType, FloatType)):
            # Si cualquiera es float, el resultado es float
            if isinstance(left_type, FloatType) or isinstance(right_type, FloatType):
                return FloatType()
            else:
                return IntType()
        else:
            raise TypeError(f"Tipos no soportados para operador '{operator}': {left_type} y {right_type}")
    
    def _check_modulo_operation(self, left_type, right_type):
        """Verifica operación módulo %"""
        if isinstance(left_type, IntType) and isinstance(right_type, IntType):
            return IntType()
        else:
            raise TypeError(f"Operador '%' solo soporta enteros: {left_type} y {right_type}")
    
    def _check_addition_operation(self, left_type, right_type):
        """Verifica operación suma +"""
        # Suma aritmética
        if isinstance(left_type, (IntType, FloatType)) and isinstance(right_type, (IntType, FloatType)):
            if isinstance(left_type, FloatType) or isinstance(right_type, FloatType):
                return FloatType()
            else:
                return IntType()
        
        # Concatenación de strings
        elif isinstance(left_type, StringType) and isinstance(right_type, StringType):
            return StringType()
        
        # Concatenación string + otro tipo (conversión implícita)
        elif isinstance(left_type, StringType) or isinstance(right_type, StringType):
            return StringType()
        
        else:
            raise TypeError(f"Tipos no soportados para operador '+': {left_type} y {right_type}")
    
    def _check_subtraction_operation(self, left_type, right_type):
        """Verifica operación resta -"""
        if isinstance(left_type, (IntType, FloatType)) and isinstance(right_type, (IntType, FloatType)):
            if isinstance(left_type, FloatType) or isinstance(right_type, FloatType):
                return FloatType()
            else:
                return IntType()
        else:
            raise TypeError(f"Tipos no soportados para operador '-': {left_type} y {right_type}")
    
    def _process_suffix_operation(self, base_type, suffix_ctx):
        """Procesa operaciones de sufijo (llamadas, indexación, etc.)"""
        # Por ahora, simplemente retorna el tipo base
        # Esto se expandirá cuando implementemos llamadas a funciones, etc.
        return base_type