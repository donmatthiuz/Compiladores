from CompiScriptParser import CompiScriptParser
from CompiScriptVisitor import CompiScriptVisitor
from custom_types import IntType, FloatType, StringType, BoolType, NullType, ArrayType, ClassType, FunctionType
from SymbolTable import SymbolTable

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
            for st in ctx.statement():
                self.visit(st)
        finally:
            self.exit_scope()
        return None

    def visitVariableDeclaration(self, ctx: CompiScriptParser.VariableDeclarationContext):
        """Maneja declaraciones de variables: let/var x = expr;"""
        var_name = ctx.Identifier().getText()
        
        # Verificar si ya existe en el scope actual
        # Usar directamente el diccionario symbols en lugar de lookup_current_scope
        if var_name in self.current_scope.symbols:
            raise NameError(f"Variable '{var_name}' ya está declarada en este ámbito")

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
            raise NameError(f"Constante '{const_name}' ya está declarada en este ámbito")

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
                raise NameError(f"Variable '{var_name}' no definida")
            value_type = self.visit(ctx.expression(0))
            if not self._are_types_compatible(symbol.type_, value_type):
                raise TypeError(f"No se puede asignar {value_type} a variable de tipo {symbol.type_}")
            return value_type

        # expression(0) '.' Identifier '=' expression(1)
        base_type = self.visit(ctx.expression(0))
        if not isinstance(base_type, ClassType):
            raise TypeError(f"Asignación a propiedad sobre un no-objeto: {base_type}")
        prop_name = ctx.Identifier(0).getText() if hasattr(ctx, "Identifier") and ctx.Identifier(0) else None
        if prop_name is None:
            raise NameError("Falta nombre de la propiedad en asignación a propiedad")

        ftype = self._resolve_field(base_type.name, prop_name)
        if ftype is None:
            if self._resolve_method(base_type.name, prop_name):
                raise TypeError(f"'{prop_name}' es un método de '{base_type.name}', no un atributo asignable")
            raise NameError(f"'{base_type.name}' no tiene atributo '{prop_name}'")

        value_type = self.visit(ctx.expression(1))
        if not self._are_types_compatible(ftype, value_type):
            raise TypeError(f"No se puede asignar {value_type} al atributo '{prop_name}' de tipo {ftype}")
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
        raise TypeError(f"Tipos incompatibles en operador ternario: {t_type} y {f_type}")

    def visitLogicalOrExpr(self, ctx: CompiScriptParser.LogicalOrExprContext):
        """Maneja OR lógico: ||"""
        if len(ctx.logicalAndExpr()) == 1:
            return self.visit(ctx.logicalAndExpr(0))
        l = self.visit(ctx.logicalAndExpr(0))
        for i in range(1, len(ctx.logicalAndExpr())):
            r = self.visit(ctx.logicalAndExpr(i))
            if not isinstance(l, BoolType) or not isinstance(r, BoolType):
                raise TypeError("Operador '||' requiere booleanos")
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
                raise TypeError("Operador '&&' requiere booleanos")
            l = BoolType()
        return l

    def visitEqualityExpr(self, ctx: CompiScriptParser.EqualityExprContext):
        """Maneja operadores de igualdad: ==, !="""
        if len(ctx.relationalExpr()) == 1:
            return self.visit(ctx.relationalExpr(0))
        _ = self.visit(ctx.relationalExpr(0))
        for i in range(1, len(ctx.relationalExpr())):
            _ = self.visit(ctx.relationalExpr(i))
        return BoolType()

    def visitRelationalExpr(self, ctx: CompiScriptParser.RelationalExprContext):
        """Maneja operadores relacionales: <, <=, >, >="""
        if len(ctx.additiveExpr()) == 1:
            return self.visit(ctx.additiveExpr(0))
        l = self.visit(ctx.additiveExpr(0))
        for i in range(1, len(ctx.additiveExpr())):
            r = self.visit(ctx.additiveExpr(i))
            if not isinstance(l, (IntType, FloatType)) or not isinstance(r, (IntType, FloatType)):
                raise TypeError("Operadores relacionales requieren operandos numéricos")
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
            raise TypeError(f"Operador unario '-' no soportado para tipo: {t}")
        else:
            if isinstance(t, BoolType):
                return BoolType()
            raise TypeError(f"Operador unario '!' no soportado para tipo: {t}")

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
        """Maneja lado izquierdo de asignaciones"""
        base_type = self.visit(ctx.primaryAtom())
        cur = base_type
        for s in ctx.suffixOp():
            cur = self._process_suffix_operation(cur, s)
        return cur

    def visitIdentifierExpr(self, ctx: CompiScriptParser.IdentifierExprContext):
        """Maneja identificadores"""
        name = ctx.Identifier().getText()
        if name == "this":
            if not (self.current_class and (self.in_method or self.in_constructor)):
                raise SyntaxError("`this` sólo puede usarse dentro de métodos o constructores de una clase")
            return ClassType(self.current_class.name)

        symbol = self.current_scope.lookup(name)
        if symbol is None:
            raise NameError(f"Variable '{name}' no definida")
        return symbol.type_

    # =====================================
    # HELPERS DE FIRMA Y TIPOS
    # =====================================
    def _extract_function_signature(self, fctx):
        """paramTypes + returnType para function/constructor dentro de clase."""
        param_types = []
        if fctx.parameters():
            for p in fctx.parameters().parameter():
                if p.type_():
                    ptype = self._parse_type_node(p.type_())
                else:
                    raise TypeError(f"Parámetro '{p.Identifier().getText()}' debe tener tipo")
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
        return t

    # =====================================
    # CLASES Y OBJETOS
    # =====================================
    def visitClassDeclaration(self, ctx: CompiScriptParser.ClassDeclarationContext):
        class_name = ctx.Identifier(0).getText()
        base_name = ctx.Identifier(1).getText() if len(ctx.Identifier()) > 1 else None

        if class_name in self.classes:
            raise NameError(f"Clase '{class_name}' ya está declarada")
        if base_name and base_name not in self.classes:
            raise NameError(f"Superclase '{base_name}' no está declarada")

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
                        raise NameError(f"Atributo '{field_name}' ya declarado en clase '{class_name}'")
                    if vctx.typeAnnotation():
                        ftype = self._parse_type_from_annotation(vctx.typeAnnotation())
                    elif vctx.initializer():
                        ftype = self.visit(vctx.initializer())
                    else:
                        raise TypeError(f"El atributo '{field_name}' en '{class_name}' debe tener tipo o valor inicial")
                    info.fields[field_name] = ftype

                elif hasattr(member, "constantDeclaration") and member.constantDeclaration():
                    cctx = member.constantDeclaration()
                    field_name = cctx.Identifier().getText()
                    if field_name in info.fields:
                        raise NameError(f"Atributo '{field_name}' ya declarado en clase '{class_name}'")
                    ftype = self.visit(cctx.expression())
                    info.fields[field_name] = ftype

                elif hasattr(member, "functionDeclaration") and member.functionDeclaration():
                    fctx = member.functionDeclaration()
                    fname = fctx.Identifier().getText()

                    param_types, ret_type = self._extract_function_signature(fctx)
                    ftype = FunctionType(param_types, ret_type)

                    if fname == "constructor":
                        if info.ctor is not None:
                            raise NameError(f"Constructor duplicado en clase '{class_name}'")
                        info.ctor = ftype

                        self.in_constructor = True
                        self.enter_scope()
                        try:
                            self.current_scope.define("this", ClassType(class_name))
                            if fctx.parameters():
                                for i, p in enumerate(fctx.parameters().parameter()):
                                    pname = p.Identifier().getText()
                                    self.current_scope.define(pname, param_types[i])
                            self.visit(fctx.block())
                        finally:
                            self.exit_scope()
                            self.in_constructor = False
                    else:
                        if fname in info.methods:
                            raise NameError(f"Método '{fname}' ya declarado en clase '{class_name}'")

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
                        self.enter_scope()
                        try:
                            self.current_scope.define("this", ClassType(class_name))
                            if fctx.parameters():
                                for i, p in enumerate(fctx.parameters().parameter()):
                                    pname = p.Identifier().getText()
                                    self.current_scope.define(pname, param_types[i])
                            self.visit(fctx.block())
                        finally:
                            self.exit_scope()
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

        info = self.classes[class_name]
        arg_types = []
        if ctx.arguments():
            exprs = [ctx.arguments().expression(i) for i in range(len(ctx.arguments().expression()))]
            arg_types = [self.visit(e) for e in exprs]

        if info.ctor is None:
            if len(arg_types) != 0:
                raise TypeError(f"La clase '{class_name}' no define constructor; se esperaban 0 argumentos")
            return ClassType(class_name)

        if len(info.ctor.param_types) != len(arg_types):
            raise TypeError(f"Constructor de '{class_name}' espera {len(info.ctor.param_types)} argumento(s), "
                            f"pero se pasaron {len(arg_types)}")
        for exp_t, got_t in zip(info.ctor.param_types, arg_types):
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
        return None

    def visitContinueStatement(self, ctx: CompiScriptParser.ContinueStatementContext):
        if self.loop_depth <= 0:
            raise SyntaxError("`continue` solo puede usarse dentro de un bucle")
        return None

    def visitSwitchStatement(self, ctx: CompiScriptParser.SwitchStatementContext):
        discr_type = self.visit(ctx.expression())
        self._require_boolean_condition(discr_type, "switch")
        return None

    # =====================================
    # FUNCIONES
    # =====================================
    def visitFunctionDeclaration(self, ctx: CompiScriptParser.FunctionDeclarationContext):
        self.function_depth += 1
        self.enter_scope()
        pushed = False
        try:
            tctx = ctx.type_()
            expected_ret = self._parse_type_node(tctx) if tctx else None
            self._function_return_stack.append(expected_ret)
            pushed = True

            # Declarar parámetros en el scope
            if ctx.parameters():
                for p in ctx.parameters().parameter():
                    pname = p.Identifier().getText()
                    ptype = self._parse_type_node(p.type_()) if p.type_() else NullType()
                    self.current_scope.define(pname, ptype)

            self.visit(ctx.block())
        finally:
            if pushed:
                self._function_return_stack.pop()
            self.exit_scope()
            self.function_depth -= 1
        return None

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
        return None

    # =====================================
    # SUFIJOS
    # =====================================
    def _process_suffix_operation(self, base_type, suffix_ctx):
        """
          - '.' Identifier           (Property)
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
                raise NameError(f"'{class_name}' no tiene miembro '{member_name}'")
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
            self.visit(suffix_ctx.expression())  # valida índice
            return base_type

        return base_type

    # =====================================
    # MÉTODOS AUXILIARES
    # =====================================
    def _require_boolean_condition(self, cond_type, where: str):
        if not isinstance(cond_type, BoolType):
            raise TypeError(f"La condición en '{where}' debe ser de tipo boolean, no {cond_type}")

    def _are_types_compatible(self, expected, actual):
        """Compatibilidad básica, con subtipado de clases y null asignable a clases."""
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
