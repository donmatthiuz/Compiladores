from CompiScriptParser import CompiScriptParser
from CompiScriptVisitor import CompiScriptVisitor
from custom_types import IntType, FloatType, StringType, BoolType, NullType, ArrayType, ClassType, FunctionType
from SymbolTable import SymbolTable

CF_RETURN = object()
CF_BREAK = object()
CF_CONTINUE = object()

class Symbol:
    def __init__(self, name, type_):
        self.name = name
        self.type_ = type_

class ClassInfo:
    def __init__(self, name, base_name=None):
        self.name = name
        self.base_name = base_name        # nombre de la superclase
        self.fields = {}                  # nombre -> Type
        self.methods = {}                 # nombre -> FunctionType
        self.ctor = None                  # FunctionType del constructor

class TypeCheckVisitor(CompiScriptVisitor):
    def __init__(self):
        self.symbol_table = SymbolTable()   # Tabla de símbolos global
        self.current_scope = self.symbol_table

        # Estado para control de flujo y funciones
        self.loop_depth = 0
        self.function_depth = 0
        self._function_return_stack = []

        # Estado para clases y objetos
        self.classes = {}
        self.current_class = None
        self.in_method = False
        self.in_constructor = False

    # ==========================
    # ÁMBITOS
    # ==========================
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

    def visitBlock(self, ctx: CompiScriptParser.BlockContext):
        self.enter_scope()
        try:
            stmts = list(ctx.statement())
            for i, st in enumerate(stmts):
                res = self.visit(st)
                if res in (CF_RETURN, CF_BREAK, CF_CONTINUE):
                    if i < len(stmts) - 1:
                        kind = "return" if res is CF_RETURN else ("break" if res is CF_BREAK else "continue")
                        line = ctx.start.line       # número de línea
                        column = ctx.start.column 
                        raise SyntaxError(f"line {line}:{column}  Código muerto: hay instrucciones después de '{kind}'")
                    return res
        finally:
            self.exit_scope()
        return None


    def visitVariableDeclaration(self, ctx: CompiScriptParser.VariableDeclarationContext):
        """Maneja declaraciones de variables: let/var x = expr;"""
        var_name = ctx.Identifier().getText()
        
        # Verificar si ya existe en el scope actual
        # Usar directamente el diccionario symbols en lugar de lookup_current_scope
        if var_name in self.current_scope.symbols:
            line = ctx.start.line       # número de línea
            column = ctx.start.column 
            raise NameError(f"line {line}:{column}  Variable '{var_name}' ya está declarada en este ámbito")

        if ctx.initializer():
            var_type = self.visit(ctx.initializer())
        elif ctx.typeAnnotation():
            var_type = self._parse_type_from_annotation(ctx.typeAnnotation())
        else:
            # Variable sin inicialización ni tipo explícito - por defecto null
            var_type = NullType()

        self.current_scope.define(var_name, var_type)
        return var_type

    def visitConstantDeclaration(self, ctx: CompiScriptParser.ConstantDeclarationContext):
        """Maneja declaraciones de constantes: const x = expr;"""
        const_name = ctx.Identifier().getText()
        
        # Verificar si ya existe
        if const_name in self.current_scope.symbols:
            line = ctx.start.line
            column = ctx.start.column 
            raise NameError(f"line {line}:{column} Constante '{const_name}' ya está declarada en este ámbito")

        const_type = self.visit(ctx.expression())
        
        # Agregar a la tabla de símbolos
        self.current_scope.define(const_name, const_type)
        return const_type

    def visitInitializer(self, ctx: CompiScriptParser.InitializerContext):
        """Maneja inicializadores: = expression"""
        return self.visit(ctx.expression())

    def visitExpressionStatement(self, ctx: CompiScriptParser.ExpressionStatementContext):
        return self.visit(ctx.expression())

    def visitPrintStatement(self, ctx: CompiScriptParser.PrintStatementContext):
        expr_type = self.visit(ctx.expression())
        return expr_type

    # =====================================
    # ASIGNACIONES
    # =====================================
    def visitAssignment(self, ctx: CompiScriptParser.AssignmentContext):
        """
          - Identifier '=' expression ';'
          - expression '.' Identifier '=' expression ';'   (asignación a propiedad)
        """
        if ctx.Identifier() and len(ctx.expression()) == 1:
            var_name = ctx.Identifier().getText()
            symbol = self.current_scope.lookup(var_name)
            if symbol is None:
                line = ctx.start.line
                column = ctx.start.column
                raise NameError(f"line {line}:{column} Variable '{var_name}' no definida")
            value_type = self.visit(ctx.expression(0))
            if not self._are_types_compatible(symbol.type_, value_type):
                line = ctx.start.line
                column = ctx.start.column
                raise TypeError(f"line {line}:{column} No se puede asignar {value_type} a variable de tipo {symbol.type_}")
            return value_type

        # expression(0) '.' Identifier '=' expression(1)
        base_type = self.visit(ctx.expression(0))
        if not isinstance(base_type, ClassType):
            line = ctx.start.line
            column = ctx.start.column 
            raise TypeError(f"line {line}:{column} Asignación a propiedad sobre un no-objeto: {base_type}")
        prop_name = ctx.Identifier().getText() if hasattr(ctx, "Identifier") and ctx.Identifier() else None
        if prop_name is None:
            line = ctx.start.line
            column = ctx.start.column 
            raise NameError(f"line {line}:{column} Falta nombre de la propiedad en asignación a propiedad")

        ftype = self._resolve_field(base_type.name, prop_name)
        line = ctx.start.line
        column = ctx.start.column 
        if ftype is None:
            if self._resolve_method(base_type.name, prop_name):
                raise TypeError(f"line {line}:{column} '{prop_name}' es un método de '{base_type.name}', no un atributo asignable")
            raise NameError(f"line {line}:{column} '{base_type.name}' no tiene atributo '{prop_name}'")

        value_type = self.visit(ctx.expression(1))
        if not self._are_types_compatible(ftype, value_type):
            raise TypeError(f"line {line}:{column} No se puede asignar {value_type} al atributo '{prop_name}' de tipo {ftype}")
        return ftype

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
        cond_t = self.visit(ctx.logicalOrExpr())
        self._require_boolean_condition(cond_t, "?:")
        t_type = self.visit(ctx.expression(0))
        f_type = self.visit(ctx.expression(1))
        if self._are_types_compatible(t_type, f_type):
            return t_type
        line = ctx.start.line
        column = ctx.start.column 
        raise TypeError(f"line {line}:{column} Tipos incompatibles en operador ternario: {t_type} y {f_type}")

    def visitLogicalOrExpr(self, ctx: CompiScriptParser.LogicalOrExprContext):
        """Maneja OR lógico: ||"""
        if len(ctx.logicalAndExpr()) == 1:
            return self.visit(ctx.logicalAndExpr(0))
        l = self.visit(ctx.logicalAndExpr(0))
        for i in range(1, len(ctx.logicalAndExpr())):
            r = self.visit(ctx.logicalAndExpr(i))
            if not isinstance(l, BoolType) or not isinstance(r, BoolType):
                line = ctx.start.line
                column = ctx.start.column
                raise TypeError(f"line {line}:{column} Operador '||' requiere booleanos")
            l = BoolType()
        return l

    def visitLogicalAndExpr(self, ctx: CompiScriptParser.LogicalAndExprContext):
        """Maneja AND lógico: &&"""
        if len(ctx.equalityExpr()) == 1:
            return self.visit(ctx.equalityExpr(0))
        l = self.visit(ctx.equalityExpr(0))
        for i in range(1, len(ctx.equalityExpr())):
            r = self.visit(ctx.equalityExpr(i))
            if not isinstance(l, BoolType) or not isinstance(r, BoolType):
                line = ctx.start.line
                column = ctx.start.column 
                raise TypeError(f"line {line}:{column} Operador '&&' requiere booleanos")
            l = BoolType()
        return l

    def visitEqualityExpr(self, ctx: CompiScriptParser.EqualityExprContext):
        """== y != con verificación de compatibilidad de tipos"""
        if len(ctx.relationalExpr()) == 1:
            return self.visit(ctx.relationalExpr(0))

        def _comparable(a, b):
            # numéricos entre si
            if isinstance(a, (IntType, FloatType)) and isinstance(b, (IntType, FloatType)):
                return True
            # mismo tipo base
            if type(a) is type(b):
                return True
            # clases con subtipado
            if (isinstance(a, ClassType) and isinstance(b, (ClassType, NullType))) or \
            (isinstance(b, ClassType) and isinstance(a, (ClassType, NullType))):
                return self._are_types_compatible(a, b) or self._are_types_compatible(b, a)
            return False

        left_t = self.visit(ctx.relationalExpr(0))
        for i in range(1, len(ctx.relationalExpr())):
            right_t = self.visit(ctx.relationalExpr(i))
            if not _comparable(left_t, right_t):
                line = ctx.start.line
                column = ctx.start.column 
                raise TypeError(f"line {line}:{column} Tipos incompatibles en comparación de igualdad: {left_t} y {right_t}")
            left_t = BoolType()
        return BoolType()


    def visitRelationalExpr(self, ctx: CompiScriptParser.RelationalExprContext):
        """Maneja operadores relacionales: <, <=, >, >="""
        if len(ctx.additiveExpr()) == 1:
            return self.visit(ctx.additiveExpr(0))
        l = self.visit(ctx.additiveExpr(0))
        for i in range(1, len(ctx.additiveExpr())):
            r = self.visit(ctx.additiveExpr(i))
            if not isinstance(l, (IntType, FloatType)) or not isinstance(r, (IntType, FloatType)):
                line = ctx.start.line
                column = ctx.start.column 
                raise TypeError(f"line {line}:{column} Operadores relacionales requieren operandos numéricos")
            l = BoolType()
        return l

    def visitAdditiveExpr(self, ctx: CompiScriptParser.AdditiveExprContext):
        """Maneja +, -"""
        if len(ctx.multiplicativeExpr()) == 1:
            # Solo hay un término, no es operación binaria
            return self.visit(ctx.multiplicativeExpr(0))
        l = self.visit(ctx.multiplicativeExpr(0))
        for i in range(1, len(ctx.multiplicativeExpr())):
            op = ctx.getChild(2*i-1).getText()
            r = self.visit(ctx.multiplicativeExpr(i))
            if op == '+':
                l = self._check_addition_operation(l, r)
            else:
                l = self._check_subtraction_operation(l, r)
        return l

    def visitMultiplicativeExpr(self, ctx: CompiScriptParser.MultiplicativeExprContext):
        """Maneja *, /, %"""
        if len(ctx.unaryExpr()) == 1:
            # Solo hay un término, no es operación binaria
            return self.visit(ctx.unaryExpr(0))
        l = self.visit(ctx.unaryExpr(0))
        for i in range(1, len(ctx.unaryExpr())):
            op = ctx.getChild(2*i-1).getText()
            r = self.visit(ctx.unaryExpr(i))
            if op in ('*', '/'):
                l = self._check_arithmetic_operation(l, r, op)
            else:
                l = self._check_modulo_operation(l, r)
        return l

    def visitUnaryExpr(self, ctx: CompiScriptParser.UnaryExprContext):
        """Maneja operadores unarios -, !"""
        if ctx.getChildCount() == 1:
            # No hay operador unario
            return self.visit(ctx.primaryExpr())
        op = ctx.getChild(0).getText()
        t = self.visit(ctx.unaryExpr())
        if op == '-':
            if isinstance(t, (IntType, FloatType)):
                return t
            line = ctx.start.line
            column = ctx.start.column 
            raise TypeError(f"line {line}:{column} Operador unario '-' no soportado para tipo: {t}")
        else:
            if isinstance(t, BoolType):
                return BoolType()
            line = ctx.start.line
            column = ctx.start.column 
            raise TypeError(f"line {line}:{column} Operador unario '!' no soportado para tipo: {t}")

    def visitPrimaryExpr(self, ctx: CompiScriptParser.PrimaryExprContext):
        """Maneja expresiones primarias"""
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        if ctx.leftHandSide():
            return self.visit(ctx.leftHandSide())
        if ctx.expression():
            return self.visit(ctx.expression())
        return None

    # =====================================
    # LITERALES E IDENTIFICADORES
    # =====================================
    def visitLiteralExpr(self, ctx: CompiScriptParser.LiteralExprContext):
        """Maneja literales"""
        if hasattr(ctx, "arrayLiteral") and ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())
        if ctx.Literal():
            lit = ctx.Literal().getText()
            if lit.startswith('"') and lit.endswith('"'):
                return StringType()
            elif lit.isdigit():
                return IntType()
        elif ctx.getText() in ('true', 'false'):
            return BoolType()
        elif ctx.getText() == 'null':
            return NullType()
        return None

    def visitLeftHandSide(self, ctx: CompiScriptParser.LeftHandSideContext):
        base_type = self.visit(ctx.primaryAtom())
        cur = base_type
        suffixes = list(ctx.suffixOp())
        for i, s in enumerate(suffixes):
            next_s = suffixes[i+1] if i+1 < len(suffixes) else None
            cur = self._process_suffix_operation(cur, s, next_s)
        return cur


    def visitIdentifierExpr(self, ctx: CompiScriptParser.IdentifierExprContext):
        """Maneja identificadores"""
        name = ctx.Identifier().getText()
        if name == "this":
            if not (self.current_class and (self.in_method or self.in_constructor)):
                line = ctx.start.line
                column = ctx.start.column 
                raise SyntaxError(f"line {line}:{column} `this` solo puede usarse dentro de métodos o constructores de una clase")
            return ClassType(self.current_class.name)

        symbol = self.current_scope.lookup(name)
        if symbol is None:
            line = ctx.start.line
            column = ctx.start.column 
            raise NameError(f"line {line}:{column} Variable '{name}' no definida")
        return symbol.type_
    
    def visitThisExpr(self, ctx: CompiScriptParser.ThisExprContext):
        """Maneja this"""
        if not (self.current_class and (self.in_method or self.in_constructor)):
            line = ctx.start.line
            column = ctx.start.column 
            raise SyntaxError(f"line {line}:{column} `this` sólo puede usarse dentro de métodos o constructores de una clase")
        return ClassType(self.current_class.name)


    # =====================================
    # HELPERS
    # =====================================
    def _extract_function_signature(self, fctx):
        """paramTypes + returnType para function/constructor dentro de clase."""
        param_types = []
        if fctx.parameters():
            for p in fctx.parameters().parameter():
                if p.type_():
                    ptype = self._parse_type_node(p.type_())
                else:
                    line = fctx.start.line
                    column = fctx.start.column 
                    raise TypeError(f"line {line}:{column} Parámetro '{p.Identifier().getText()}' debe tener tipo")
                param_types.append(ptype)
        ret_type = self._parse_type_node(fctx.type_()) if fctx.type_() else NullType()
        return param_types, ret_type

    def _parse_type_from_annotation(self, ann_ctx):
        return self._parse_type_node(ann_ctx.type_())

    def _parse_type_node(self, type_ctx):
        base = type_ctx.baseType().getText()
        if base == 'integer':
            t = IntType()
        elif base == 'string':
            t = StringType()
        elif base == 'boolean':
            t = BoolType()
        else:
            t = ClassType(base)

        dims = type_ctx.getText().count('[]')
        for _ in range(dims):
            t = ArrayType(t)
        return t


    # =====================================
    # CLASES Y OBJETOS
    # =====================================
    def visitClassDeclaration(self, ctx: CompiScriptParser.ClassDeclarationContext):
        class_name = ctx.Identifier(0).getText()
        base_name = ctx.Identifier(1).getText() if len(ctx.Identifier()) > 1 else None

        if class_name in self.classes:
            line = ctx.start.line
            column = ctx.start.column 
            raise NameError(f"line {line}:{column} Clase '{class_name}' ya está declarada")
        if base_name and base_name not in self.classes:
            line = ctx.start.line
            column = ctx.start.column
            raise NameError(f"line {line}:{column} Superclase '{base_name}' no está declarada")

        info = ClassInfo(class_name, base_name)
        self.classes[class_name] = info

        prev_class, prev_method, prev_ctor = self.current_class, self.in_method, self.in_constructor
        self.current_class, self.in_method, self.in_constructor = info, False, False

        self.enter_scope()
        try:
            # classMember: functionDeclaration | variableDeclaration | constantDeclaration
            for member in getattr(ctx, "classMember", lambda: [])():
                if hasattr(member, "variableDeclaration") and member.variableDeclaration():
                    vctx = member.variableDeclaration()
                    field_name = vctx.Identifier().getText()
                    if field_name in info.fields:
                        line = vctx.start.line
                        column = vctx.start.column 

                        raise NameError(f"line {line}:{column} Atributo '{field_name}' ya declarado en clase '{class_name}'")
                    if vctx.typeAnnotation():
                        ftype = self._parse_type_from_annotation(vctx.typeAnnotation())
                    elif vctx.initializer():
                        ftype = self.visit(vctx.initializer())
                    else:
                        line = vctx.start.line
                        column = vctx.start.column 

                        raise TypeError(f"line {line}:{column} El atributo '{field_name}' en '{class_name}' debe tener tipo o valor inicial")
                    info.fields[field_name] = ftype

                elif hasattr(member, "constantDeclaration") and member.constantDeclaration():
                    cctx = member.constantDeclaration()
                    field_name = cctx.Identifier().getText()
                    if field_name in info.fields:
                        line = cctx.start.line
                        column = cctx.start.column 

                        raise NameError(f"line {line}:{column} Atributo '{field_name}' ya declarado en clase '{class_name}'")
                    ftype = self.visit(cctx.expression())
                    info.fields[field_name] = ftype

                elif hasattr(member, "functionDeclaration") and member.functionDeclaration():
                    fctx = member.functionDeclaration()
                    fname = fctx.Identifier().getText()

                    # Firma del miembro
                    param_types, ret_type = self._extract_function_signature(fctx)
                    ftype = FunctionType(param_types, ret_type)

                    if fname == "constructor":
                        if info.ctor is not None:
                            line = fctx.start.line
                            column = fctx.start.column 

                            raise NameError(f"line {line}:{column} Constructor duplicado en clase '{class_name}'")
                        info.ctor = ftype

                        self.in_constructor = True
                        self.function_depth += 1
                        self.enter_scope()
                        try:
                            # 'this' en el scope
                            self.current_scope.define("this", ClassType(class_name))

                            # Duplicados en parámetros
                            seen = set()
                            if fctx.parameters():
                                for i, p in enumerate(fctx.parameters().parameter()):
                                    pname = p.Identifier().getText()
                                    if pname in seen:
                                        raise NameError(f"Parámetro duplicado '{pname}'")
                                    seen.add(pname)
                                    self.current_scope.define(pname, param_types[i])

                            # retorno esperado en constructor: null/void
                            self._function_return_stack.append(NullType())
                            try:
                                self.visit(fctx.block())
                            finally:
                                self._function_return_stack.pop()
                        finally:
                            self.exit_scope()
                            self.function_depth -= 1
                            self.in_constructor = False

                    else:
                        if fname in info.methods:
                            raise NameError(f"Método '{fname}' ya declarado en clase '{class_name}'")

                        # Override con superclase
                        super_m = self._resolve_method(class_name, fname) if info.base_name else None
                        if super_m:
                            if len(super_m.param_types) != len(param_types):
                                raise TypeError(f"Firma incompatible al sobreescribir '{fname}' en '{class_name}'")
                            for sp, pp in zip(super_m.param_types, param_types):
                                if not self._are_types_compatible(sp, pp) or not self._are_types_compatible(pp, sp):
                                    raise TypeError(f"Firma incompatible al sobreescribir '{fname}' en '{class_name}'")
                            if not self._are_types_compatible(super_m.return_type, ret_type) or \
                            not self._are_types_compatible(ret_type, super_m.return_type):
                                raise TypeError(f"Tipo de retorno incompatible al sobreescribir '{fname}' en '{class_name}'")

                        info.methods[fname] = ftype

                        self.in_method = True
                        self.function_depth += 1
                        self.enter_scope()
                        try:
                            self.current_scope.define("this", ClassType(class_name))

                            # Duplicados en parámetros
                            seen = set()
                            if fctx.parameters():
                                for i, p in enumerate(fctx.parameters().parameter()):
                                    pname = p.Identifier().getText()
                                    if pname in seen:
                                        raise NameError(f"Parámetro duplicado '{pname}'")
                                    seen.add(pname)
                                    self.current_scope.define(pname, param_types[i])

                            self._function_return_stack.append(ret_type)
                            try:
                                self.visit(fctx.block())
                            finally:
                                self._function_return_stack.pop()
                        finally:
                            self.exit_scope()
                            self.function_depth -= 1
                            self.in_method = False

                else:
                    pass
        finally:
            self.exit_scope()
            self.current_class, self.in_method, self.in_constructor = prev_class, prev_method, prev_ctor
        return None

    def visitNewExpr(self, ctx: CompiScriptParser.NewExprContext):
        class_name = ctx.Identifier().getText()
        if class_name not in self.classes:
            raise NameError(f"Clase '{class_name}' no está declarada")

        arg_types = []
        if ctx.arguments():
            exprs = [ctx.arguments().expression(i) for i in range(len(ctx.arguments().expression()))]
            arg_types = [self.visit(e) for e in exprs]

        ctor = self._resolve_ctor(class_name)

        if ctor is None:
            if len(arg_types) != 0:
                raise TypeError(f"La clase '{class_name}' no define constructor; se esperaban 0 argumentos")
            return ClassType(class_name)

        if len(ctor.param_types) != len(arg_types):
            raise TypeError(
                f"Constructor de '{class_name}' espera {len(ctor.param_types)} argumento(s), "
                f"pero se pasaron {len(arg_types)}"
            )
        for exp_t, got_t in zip(ctor.param_types, arg_types):
            if not self._are_types_compatible(exp_t, got_t):
                raise TypeError(f"Argumento de constructor incompatible: se esperaba {exp_t}, recibido {got_t}")

        return ClassType(class_name)


    # =====================================
    # CONTROL DE FLUJO
    # =====================================
    def visitIfStatement(self, ctx: CompiScriptParser.IfStatementContext):
        cond_t = self.visit(ctx.expression())
        self._require_boolean_condition(cond_t, "if")
        self.visit(ctx.block(0))
        if ctx.block(1):
            self.visit(ctx.block(1))
        return None

    def visitWhileStatement(self, ctx: CompiScriptParser.WhileStatementContext):
        cond_t = self.visit(ctx.expression())
        self._require_boolean_condition(cond_t, "while")
        self.loop_depth += 1
        try:
            self.visit(ctx.block())
        finally:
            self.loop_depth -= 1
        return None

    def visitDoWhileStatement(self, ctx: CompiScriptParser.DoWhileStatementContext):
        self.loop_depth += 1
        try:
            self.visit(ctx.block())
        finally:
            self.loop_depth -= 1
        cond_t = self.visit(ctx.expression())
        self._require_boolean_condition(cond_t, "do-while")
        return None

    def visitForStatement(self, ctx: CompiScriptParser.ForStatementContext):
        if ctx.variableDeclaration():
            self.visit(ctx.variableDeclaration())
        elif ctx.assignment():
            self.visit(ctx.assignment())

        if ctx.expression(0):
            self._require_boolean_condition(self.visit(ctx.expression(0)), "for")
        if ctx.expression(1):
            self.visit(ctx.expression(1))

        self.loop_depth += 1
        try:
            self.visit(ctx.block())
        finally:
            self.loop_depth -= 1
        return None

    def visitForeachStatement(self, ctx: CompiScriptParser.ForeachStatementContext):
        self.loop_depth += 1
        try:
            self.visit(ctx.expression())
            self.visit(ctx.block())
        finally:
            self.loop_depth -= 1
        return None

    def visitBreakStatement(self, ctx: CompiScriptParser.BreakStatementContext):
        if self.loop_depth <= 0:
            raise SyntaxError("`break` solo puede usarse dentro de un bucle")
        return CF_BREAK

    def visitContinueStatement(self, ctx: CompiScriptParser.ContinueStatementContext):
        if self.loop_depth <= 0:
            raise SyntaxError("`continue` solo puede usarse dentro de un bucle")
        return CF_CONTINUE

    
    
    def visitSwitchStatement(self, ctx: CompiScriptParser.SwitchStatementContext):

        discr_type = self.visit(ctx.expression())

        # Revisar cada case
        for case_ctx in ctx.switchCase():
            case_expr_type = self.visit(case_ctx.expression())

            if not self._are_types_compatible(discr_type, case_expr_type):
                token = case_ctx.expression().start
                line, col = token.line, token.column
                raise TypeError(
                    f"line {line}:{col}  error: Los case deben ser del mismo tipo que el switch: "
                    f"switch es {discr_type}, pero este case es {case_expr_type}"
                )

            # Chequear todas las sentencias dentro del case
            for stmt in case_ctx.statement():
                self.visit(stmt)

        # Revisar default
        if ctx.defaultCase():
            for stmt in ctx.defaultCase().statement():
                self.visit(stmt)

        return None




    


    # =====================
    # TRY / CATCH
    # =====================
    def _visit_try_catch_core(self, ctx):
        # try { ... }
        self.visit(ctx.block(0))

        # catch (err) { ... }
        self.enter_scope()
        try:
            catch_name = ctx.Identifier().getText() if hasattr(ctx, "Identifier") and ctx.Identifier() else "_err"
            if catch_name in self.current_scope.symbols:
                raise NameError(f"Variable '{catch_name}' ya está declarada en este ámbito")

            self.current_scope.define(catch_name, NullType())

            self.visit(ctx.block(1))
        finally:
            self.exit_scope()
        return None

    def visitTryCatchStatement(self, ctx):
        return self._visit_try_catch_core(ctx)

    def visitTryStatement(self, ctx):
        return self._visit_try_catch_core(ctx)

    # =====================================
    # FUNCIONES
    # =====================================
    def visitFunctionDeclaration(self, ctx: CompiScriptParser.FunctionDeclarationContext):
        # Firma y registro del símbolo de la función en el scope actual
        fname = ctx.Identifier().getText()
        param_types = []
        if ctx.parameters():
            for p in ctx.parameters().parameter():
                if p.type_():
                    param_types.append(self._parse_type_node(p.type_()))
                else:
                    raise TypeError(f"Parámetro '{p.Identifier().getText()}' debe tener tipo")
        ret_type = self._parse_type_node(ctx.type_()) if ctx.type_() else NullType()

        # Define el símbolo de la función
        self.current_scope.define(fname, FunctionType(param_types, ret_type))

        # Detecta parámetros duplicados
        seen = set()
        for p in ctx.parameters().parameter() if ctx.parameters() else []:
            pname = p.Identifier().getText()
            if pname in seen:
                raise NameError(f"Parámetro duplicado '{pname}'")
            seen.add(pname)

        # Scope de la función
        self.function_depth += 1
        self.enter_scope()
        pushed = False
        try:
            # declara parámetros en el scope
            if ctx.parameters():
                for i, p in enumerate(ctx.parameters().parameter()):
                    pname = p.Identifier().getText()
                    self.current_scope.define(pname, param_types[i])

            self._function_return_stack.append(ret_type)
            pushed = True
            self.visit(ctx.block())
        finally:
            if pushed:
                self._function_return_stack.pop()
            self.exit_scope()
            self.function_depth -= 1
        return None

    def visitCallExpr(self, ctx: CompiScriptParser.CallExprContext):
        fname = ctx.parentCtx.primaryAtom().getText() if hasattr(ctx.parentCtx, "primaryAtom") else None

        # Evalúa los argumentos
        arg_types = []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                arg_types.append(self.visit(e))

        # Verifica que la función exista en el scope
        ftype = self.current_scope.resolve(fname)
        if not isinstance(ftype, FunctionType):
            token = ctx.start
            raise TypeError(f"line {token.line}:{token.column}  error: '{fname}' no es una función")

        # Verifica número de parámetros
        if len(arg_types) != len(ftype.param_types):
            token = ctx.start
            raise TypeError(
                f"line {token.line}:{token.column}  error: La función '{fname}' esperaba {len(ftype.param_types)} "
                f"argumentos pero recibió {len(arg_types)}"
            )

        # Verifica tipos de parámetros
        for i, (expected, actual) in enumerate(zip(ftype.param_types, arg_types)):
            if not self._are_types_compatible(expected, actual):
                token = ctx.arguments().expression(i).start
                raise TypeError(
                    f"line {token.line}:{token.column}  error: argumento {i+1} de '{fname}' "
                    f"espera {expected}, recibió {actual}"
                )

        return ftype.ret_type


    def visitReturnStatement(self, ctx: CompiScriptParser.ReturnStatementContext):
        if self.function_depth <= 0:
            raise SyntaxError("`return` debe estar dentro del cuerpo de una función")
        expected = self._function_return_stack[-1] if self._function_return_stack else None
        if ctx.expression():
            actual = self.visit(ctx.expression())
            if expected is not None and not self._are_types_compatible(expected, actual):
                raise TypeError(f"El tipo de retorno esperado es {expected}, pero se retornó {actual}")
        else:
            if expected is not None and str(expected) != "null":
                raise TypeError(f"Se esperaba retorno de tipo {expected}, pero se encontró `return;` vacío")
        return CF_RETURN

    # =====================================
    # SUFIJOS
    # =====================================
    def _process_suffix_operation(self, base_type, suffix_ctx, next_suffix_ctx=None):
        """
          - '.' Identifier           (Property o acceso a método)
          - '(' arguments? ')'       (Call)
          - '[' expression ']'       (Index)
        """
        first = suffix_ctx.getChild(0).getText()

        # Propiedad: .id
        if first == '.':
            if not isinstance(base_type, ClassType):
                raise TypeError(f"Acceso a miembro sobre no-objeto: {base_type}")
            member_name = suffix_ctx.Identifier().getText()
            class_name = base_type.name

            mtype = self._resolve_method(class_name, member_name)
            if mtype:
                return mtype

            ftype = self._resolve_field(class_name, member_name)
            if ftype is None:
                is_next_call = (
                    next_suffix_ctx is not None and
                    next_suffix_ctx.getChildCount() > 0 and
                    next_suffix_ctx.getChild(0).getText() == '('
                )
                if is_next_call:
                    raise NameError(f"'{class_name}' no tiene miembro '{member_name}'")
                raise NameError(f"'{class_name}' no tiene atributo '{member_name}'")
            return ftype

        # Llamada: (args)
        if first == '(':
            if not isinstance(base_type, FunctionType):
                raise TypeError(f"Intenta de llamar a algo no invocable: {base_type}")
            arg_types = []
            if suffix_ctx.arguments():
                exprs = [suffix_ctx.arguments().expression(i) for i in range(len(suffix_ctx.arguments().expression()))]
                arg_types = [self.visit(e) for e in exprs]
            if len(base_type.param_types) != len(arg_types):
                raise TypeError(f"Se esperaban {len(base_type.param_types)} argumento(s), pero llegaron {len(arg_types)}")
            for exp_t, got_t in zip(base_type.param_types, arg_types):
                if not self._are_types_compatible(exp_t, got_t):
                    raise TypeError(f"Argumento incompatible: esperado {exp_t}, recibido {got_t}")
            return base_type.return_type

        # Indexación: [expr]
        if first == '[':
            idx_t = self.visit(suffix_ctx.expression())
            if not isinstance(idx_t, IntType):
                raise TypeError("Índice de lista debe ser integer")
            if not isinstance(base_type, ArrayType):
                raise TypeError(f"Indexación sobre no-lista: {base_type}")
            return base_type.element_type

        return base_type


    # ====================================== 
    # ARREGLOS
    # ======================================
    def visitArrayLiteral(self, ctx: CompiScriptParser.ArrayLiteralContext):
        n = len(ctx.expression())
        if n == 0:
            from custom_types import NullType
            return ArrayType(NullType())

        # Tipo del primer elemento
        elem_t = self.visit(ctx.expression(0))

        for i in range(1, n):
            t = self.visit(ctx.expression(i))
            if not (self._are_types_compatible(elem_t, t) or self._are_types_compatible(t, elem_t)):
                line = ctx.start.line
                column = ctx.start.column 
                raise TypeError(f"line {line}:{column} Elementos de la lista deben ser del mismo tipo: {elem_t} y {t}")
            if isinstance(elem_t, ClassType) and isinstance(t, ClassType) and elem_t.name != t.name:
                if self._is_subclass(t.name, elem_t.name):
                    # t <: elem_t  => nos quedamos con elem_t
                    pass
                elif self._is_subclass(elem_t.name, t.name):
                    # elem_t <: t  => elevamos a t
                    elem_t = t
                else:
                    line = ctx.start.line
                    column = ctx.start.column 
                    raise TypeError(f"line {line}:{column} Elementos de la lista deben ser del mismo tipo: {elem_t} y {t}")

        return ArrayType(elem_t)


    # =====================================
    # MÉTODOS AUXILIARES
    # =====================================
    def _require_boolean_condition(self, cond_type, where: str):
        if not isinstance(cond_type, BoolType):
            raise TypeError(f"La condición en '{where}' debe ser de tipo boolean, no {cond_type}")

    def _are_types_compatible(self, expected, actual):
        """Compatibilidad básica, con subtipado de clases, null para clases y arrays recursivos."""

        if isinstance(expected, ArrayType) and isinstance(actual, ArrayType):
            return self._are_types_compatible(expected.element_type, actual.element_type)

        if type(expected) is type(actual):
            if isinstance(expected, ClassType) and isinstance(actual, ClassType):
                return self._is_subclass(actual.name, expected.name)
            return True
        if isinstance(actual, NullType) and isinstance(expected, ClassType):
            return True
        if isinstance(expected, ClassType) and isinstance(actual, ClassType):
            return self._is_subclass(actual.name, expected.name)
        return False

    def _is_subclass(self, sub_name, super_name):
        if sub_name == super_name:
            return True
        info = self.classes.get(sub_name)
        while info and info.base_name:
            if info.base_name == super_name:
                return True
            info = self.classes.get(info.base_name)
        return False

    def _resolve_field(self, class_name, field_name):
        info = self.classes.get(class_name)
        while info:
            if field_name in info.fields:
                return info.fields[field_name]
            info = self.classes.get(info.base_name) if info.base_name else None
        return None

    def _resolve_method(self, class_name, method_name):
        info = self.classes.get(class_name)
        while info:
            if method_name in info.methods:
                return info.methods[method_name]
            info = self.classes.get(info.base_name) if info.base_name else None
        return None

    def _resolve_ctor(self, class_name):
        """Devuelve el primer constructor accesible en la jerarquía"""
        info = self.classes.get(class_name)
        while info:
            if info.ctor is not None:
                return info.ctor
            info = self.classes.get(info.base_name) if info.base_name else None
        return None


    # =====================================
    # OPERACIONES ARITMÉTICAS
    # =====================================
    def _check_arithmetic_operation(self, left_type, right_type, operator):
        if isinstance(left_type, (IntType, FloatType)) and isinstance(right_type, (IntType, FloatType)):
            if isinstance(left_type, FloatType) or isinstance(right_type, FloatType):
                return FloatType()
            return IntType()
        raise TypeError(f"Tipos no soportados para operador '{operator}': {left_type} y {right_type}")

    def _check_modulo_operation(self, left_type, right_type):
        if isinstance(left_type, IntType) and isinstance(right_type, IntType):
            return IntType()
        raise TypeError(f"Operador '%' solo soporta enteros: {left_type} y {right_type}")

    def _check_addition_operation(self, left_type, right_type):
        if isinstance(left_type, (IntType, FloatType)) and isinstance(right_type, (IntType, FloatType)):
            if isinstance(left_type, FloatType) or isinstance(right_type, FloatType):
                return FloatType()
            return IntType()
        if isinstance(left_type, StringType) and isinstance(right_type, StringType):
            return StringType()
        if isinstance(left_type, StringType) or isinstance(right_type, StringType):
            return StringType()
        raise TypeError(f"Tipos no soportados para operador '+': {left_type} y {right_type}")

    def _check_subtraction_operation(self, left_type, right_type):
        if isinstance(left_type, (IntType, FloatType)) and isinstance(right_type, (IntType, FloatType)):
            if isinstance(left_type, FloatType) or isinstance(right_type, FloatType):
                return FloatType()
            return IntType()
        raise TypeError(f"Tipos no soportados para operador '-': {left_type} y {right_type}")
