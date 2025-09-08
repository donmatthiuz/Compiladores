from CompiScriptParser import CompiScriptParser
from CompiScriptVisitor import CompiScriptVisitor
from custom_types import IntType, FloatType, StringType, BoolType, NullType, ArrayType, ClassType, FunctionType
from SymbolTable import SymbolTable

class Symbol:
    def __init__(self, name, type_):
        self.name = name
        self.type_ = type_

class TypeCheckVisitor(CompiScriptVisitor):
    def __init__(self):
        self.symbol_table = SymbolTable()  # Tabla de símbolos global
        self.current_scope = self.symbol_table
        self.loop_depth = 0                # anidamiento actual de bucles
        self.function_depth = 0            # anidamiento actual de funciones
        self._function_return_stack = []   # pila del tipo de retorno esperado
        
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
    # PROGRAMA Y STATEMENTS
    # =====================================
    
    def visitProgram(self, ctx: CompiScriptParser.ProgramContext):
        """Visita el programa principal"""
        for statement in ctx.statement():
            self.visit(statement)
        return None
    
    def visitVariableDeclaration(self, ctx: CompiScriptParser.VariableDeclarationContext):
        """Maneja declaraciones de variables: let/var x = expr;"""
        var_name = ctx.Identifier().getText()
        
        # Verificar si ya existe en el scope actual
        # Usar directamente el diccionario symbols en lugar de lookup_current_scope
        if var_name in self.current_scope.symbols:
            raise NameError(f"Variable '{var_name}' ya está declarada en este ámbito")
        
        # Obtener tipo de la expresión inicializadora
        var_type = None
        if ctx.initializer():
            var_type = self.visit(ctx.initializer())
        elif ctx.typeAnnotation():
            var_type = self._parse_type_annotation(ctx.typeAnnotation())
        else:
            # Variable sin inicialización ni tipo explícito - por defecto null
            var_type = NullType()
        
        # Agregar a la tabla de símbolos
        # Usar el método define que ya existe en SymbolTable
        self.current_scope.define(var_name, var_type)
        return var_type
    
    def visitConstantDeclaration(self, ctx: CompiScriptParser.ConstantDeclarationContext):
        """Maneja declaraciones de constantes: const x = expr;"""
        const_name = ctx.Identifier().getText()
        
        # Verificar si ya existe
        if const_name in self.current_scope.symbols:
            raise NameError(f"Constante '{const_name}' ya está declarada en este ámbito")
        
        # Las constantes DEBEN tener inicializador
        const_type = self.visit(ctx.expression())
        
        # Agregar a la tabla de símbolos
        self.current_scope.define(const_name, const_type)
        return const_type
    
    def visitInitializer(self, ctx: CompiScriptParser.InitializerContext):
        """Maneja inicializadores: = expression"""
        return self.visit(ctx.expression())
    
    def visitAssignment(self, ctx: CompiScriptParser.AssignmentContext):
        """Maneja asignaciones: x = expr;"""
        if ctx.Identifier():
            # Asignación simple: x = expr;
            var_name = ctx.Identifier().getText()
            symbol = self.current_scope.lookup(var_name)
            
            if symbol is None:
                raise NameError(f"Variable '{var_name}' no definida")
            
            expr_type = self.visit(ctx.expression(0))
            
            # Verificar compatibilidad de tipos
            if not self._are_types_compatible(symbol.type_, expr_type):
                raise TypeError(f"No se puede asignar {expr_type} a variable de tipo {symbol.type_}")
            
            return expr_type
        else:
            # Asignación a propiedad: obj.prop = expr;
            # Por ahora, simplemente visitar la expresión
            return self.visit(ctx.expression(0))
    
    def visitExpressionStatement(self, ctx: CompiScriptParser.ExpressionStatementContext):
        """Maneja statements de expresión: expr;"""
        return self.visit(ctx.expression())
    
    def visitPrintStatement(self, ctx: CompiScriptParser.PrintStatementContext):
        """Maneja statements de print: print(expr);"""
        expr_type = self.visit(ctx.expression())
        print(f"[PRINT] Expresión de tipo: {expr_type}")
        return expr_type

    # =====================================
    # EXPRESIONES
    # =====================================
    
    def visitExpression(self, ctx: CompiScriptParser.ExpressionContext):
        """Maneja expresiones generales"""
        return self.visit(ctx.assignmentExpr())
    
    def visitExprNoAssign(self, ctx: CompiScriptParser.ExprNoAssignContext):
        """Maneja expresiones sin asignación"""
        return self.visit(ctx.conditionalExpr())
    
    def visitTernaryExpr(self, ctx: CompiScriptParser.TernaryExprContext):
        """Maneja expresiones ternarias: condition ? expr1 : expr2"""
        if len(ctx.children) == 1:
            # No es ternario, solo logicalOrExpr
            return self.visit(ctx.logicalOrExpr())
        
        # Es ternario
        condition_type = self.visit(ctx.logicalOrExpr())
        if not isinstance(condition_type, BoolType):
            raise TypeError(f"La condición del operador ternario debe ser booleana, no {condition_type}")
        
        true_type = self.visit(ctx.expression(0))
        false_type = self.visit(ctx.expression(1))
        
        # El tipo resultado debe ser compatible entre ambas ramas
        if self._are_types_compatible(true_type, false_type):
            return true_type
        else:
            raise TypeError(f"Tipos incompatibles en operador ternario: {true_type} y {false_type}")
    
    def visitLogicalOrExpr(self, ctx: CompiScriptParser.LogicalOrExprContext):
        """Maneja OR lógico: ||"""
        if len(ctx.logicalAndExpr()) == 1:
            return self.visit(ctx.logicalAndExpr(0))
        
        result_type = self.visit(ctx.logicalAndExpr(0))
        for i in range(1, len(ctx.logicalAndExpr())):
            right_type = self.visit(ctx.logicalAndExpr(i))
            if not isinstance(result_type, BoolType) or not isinstance(right_type, BoolType):
                raise TypeError(f"Operador '||' requiere operandos booleanos")
            result_type = BoolType()
        
        return result_type
    
    def visitLogicalAndExpr(self, ctx: CompiScriptParser.LogicalAndExprContext):
        """Maneja AND lógico: &&"""
        if len(ctx.equalityExpr()) == 1:
            return self.visit(ctx.equalityExpr(0))
        
        result_type = self.visit(ctx.equalityExpr(0))
        for i in range(1, len(ctx.equalityExpr())):
            right_type = self.visit(ctx.equalityExpr(i))
            if not isinstance(result_type, BoolType) or not isinstance(right_type, BoolType):
                raise TypeError(f"Operador '&&' requiere operandos booleanos")
            result_type = BoolType()
        
        return result_type
    
    def visitEqualityExpr(self, ctx: CompiScriptParser.EqualityExprContext):
        """Maneja operadores de igualdad: ==, !="""
        if len(ctx.relationalExpr()) == 1:
            return self.visit(ctx.relationalExpr(0))
        
        result_type = self.visit(ctx.relationalExpr(0))
        for i in range(1, len(ctx.relationalExpr())):
            operator = ctx.getChild(2*i-1).getText()  # == o !=
            right_type = self.visit(ctx.relationalExpr(i))
            # Los operadores de igualdad siempre retornan boolean
            result_type = BoolType()
        
        return result_type
    
    def visitRelationalExpr(self, ctx: CompiScriptParser.RelationalExprContext):
        """Maneja operadores relacionales: <, <=, >, >="""
        if len(ctx.additiveExpr()) == 1:
            return self.visit(ctx.additiveExpr(0))
        
        result_type = self.visit(ctx.additiveExpr(0))
        for i in range(1, len(ctx.additiveExpr())):
            operator = ctx.getChild(2*i-1).getText()  # <, <=, >, >=
            right_type = self.visit(ctx.additiveExpr(i))
            
            # Verificar que ambos operandos sean numéricos
            if not isinstance(result_type, (IntType, FloatType)) or not isinstance(right_type, (IntType, FloatType)):
                raise TypeError(f"Operador '{operator}' requiere operandos numéricos")
            
            # Los operadores relacionales siempre retornan boolean
            result_type = BoolType()
        
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
    
    # =====================================
    # LITERALES E IDENTIFICADORES
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
    
    def visitLeftHandSide(self, ctx: CompiScriptParser.LeftHandSideContext):
        """Maneja lado izquierdo de asignaciones"""
        base_type = self.visit(ctx.primaryAtom())
        
        # Procesar operaciones de sufijo (llamadas, indexación, acceso a propiedades)
        current_type = base_type
        for suffix in ctx.suffixOp():
            current_type = self._process_suffix_operation(current_type, suffix)
        
        return current_type
    
    def visitIdentifierExpr(self, ctx: CompiScriptParser.IdentifierExprContext):
        """Maneja identificadores"""
        name = ctx.Identifier().getText()
        symbol = self.current_scope.lookup(name)
        
        if symbol is None:
            raise NameError(f"Variable '{name}' no definida")
        
        return symbol.type_
    
    # =====================================
    # MÉTODOS AUXILIARES
    # =====================================
    
    def _parse_type_annotation(self, ctx):
        """Parsea anotaciones de tipo"""
        type_ctx = ctx.type_()
        base_type_text = type_ctx.baseType().getText()
        
        if base_type_text == 'integer':
            return IntType()
        elif base_type_text == 'string':
            return StringType()
        elif base_type_text == 'boolean':
            return BoolType()
        else:
            # Tipo personalizado (clase)
            return ClassType(base_type_text)
    
    def _are_types_compatible(self, expected, actual):
        """Verifica si dos tipos son compatibles"""
        if type(expected) == type(actual):
            return True
        # Null es compatible con cualquier tipo
        if isinstance(actual, NullType):
            return True
        return False
    
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
    
    # ===============================
    # CONTROL DE FLUJO
    # ===============================

    # if (...) statement (else statement)?
    def visitIfStatement(self, ctx):
        cond_t = self.visit(ctx.expression())
        self._require_boolean_condition(cond_t, "if")
        self.visit(ctx.statement(0))
        if len(ctx.statement()) > 1:
            self.visit(ctx.statement(1))
        return None

    # while (...) statement
    def visitWhileStatement(self, ctx):
        cond_t = self.visit(ctx.expression())
        self._require_boolean_condition(cond_t, "while")
        self.loop_depth += 1
        try:
            self.visit(ctx.statement())
        finally:
            self.loop_depth -= 1
        return None

    # do statement while (...);
    def visitDoWhileStatement(self, ctx):
        self.loop_depth += 1
        try:
            self.visit(ctx.statement()) 
        finally:
            self.loop_depth -= 1
        cond_t = self.visit(ctx.expression())
        self._require_boolean_condition(cond_t, "do-while")
        return None

    # for (init? ; cond? ; update?) statement
    def visitForStatement(self, ctx):
        # init
        if hasattr(ctx, "init") and ctx.init():
            self.visit(ctx.init())
        elif hasattr(ctx, "initializer") and ctx.initializer():
            self.visit(ctx.initializer())

        # cond
        cond_t = None
        if hasattr(ctx, "cond") and ctx.cond():
            cond_t = self.visit(ctx.cond())
        elif hasattr(ctx, "condition") and ctx.condition():
            cond_t = self.visit(ctx.condition())
        elif hasattr(ctx, "expression") and ctx.expression():
            cond_t = self.visit(ctx.expression(0))

        if cond_t is not None:
            self._require_boolean_condition(cond_t, "for")

        self.loop_depth += 1
        try:
            # evaluamos para type-checking
            if hasattr(ctx, "update") and ctx.update():
                self.visit(ctx.update())
            elif hasattr(ctx, "expression") and len(ctx.expression()) > 1:
                self.visit(ctx.expression(1))
            # cuerpo
            self.visit(ctx.statement())
        finally:
            self.loop_depth -= 1
        return None

    # foreach (x in coleccion) statement
    def visitForeachStatement(self, ctx):
        self.loop_depth += 1
        try:
            self.visit(ctx.expression())
            self.visit(ctx.statement())
        finally:
            self.loop_depth -= 1
        return None

    # break;
    def visitBreakStatement(self, ctx):
        if self.loop_depth <= 0:
            raise SyntaxError("`break` solo puede usarse dentro de un bucle")
        return None

    # continue;
    def visitContinueStatement(self, ctx):
        if self.loop_depth <= 0:
            raise SyntaxError("`continue` solo puede usarse dentro de un bucle")
        return None

    def _require_boolean_condition(self, cond_type, where: str):
        from custom_types import BoolType
        if not isinstance(cond_type, BoolType):
            raise TypeError(f"La condición en '{where}' debe ser de tipo boolean, no {cond_type}")
        
    # switch (...) { ... }
    def visitSwitchStatement(self, ctx):
        discr_type = self.visit(ctx.expression())
        self._require_boolean_condition(discr_type, "switch")
        for i in range(len(ctx.switchBlock().switchSection())):
            self.visit(ctx.switchBlock().switchSection(i))
        return None

    # ===============================
    # FUNCIONES Y RETURN
    # ===============================

    # function fname(params): Type { ... }
    def visitFunctionDeclaration(self, ctx):
        # Entra a un nuevo scope para la función
        self.function_depth += 1
        self.enter_scope()
        try:
            expected_ret = None
            if hasattr(ctx, "typeAnnotation") and ctx.typeAnnotation():
                expected_ret = self._parse_type_annotation(ctx.typeAnnotation())
            self._function_return_stack.append(expected_ret)

            if hasattr(ctx, "block") and ctx.block():
                self.visit(ctx.block())
            elif hasattr(ctx, "statement") and ctx.statement():
                self.visit(ctx.statement())
        finally:
            self._function_return_stack.pop()
            self.exit_scope()
            self.function_depth -= 1
        return None

    # return; | return expr;
    def visitReturnStatement(self, ctx):
        if self.function_depth <= 0:
            raise SyntaxError("`return` debe estar dentro del cuerpo de una función")

        expected = self._function_return_stack[-1] if self._function_return_stack else None
        if hasattr(ctx, "expression") and ctx.expression():
            actual = self.visit(ctx.expression())
            if expected is not None and not self._are_types_compatible(expected, actual):
                raise TypeError(f"El tipo de retorno esperado es {expected}, pero se retornó {actual}")
        else:
            # return sin expresión
            if expected is not None and str(expected) != "null":
                raise TypeError(f"Se esperaba retorno de tipo {expected}, pero se encontró `return;` vacío")
        return None