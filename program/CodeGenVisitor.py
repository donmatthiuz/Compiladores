from CompiScriptVisitor import CompiScriptVisitor
from QuadrupleTable import QuadrupleTable

class CodeGenVisitor(CompiScriptVisitor):
    def __init__(self, linked_table, symbol_table):
        """
        linked_table: LinkedTable para navegación de scopes
        symbol_table: SymbolTable original para lookup de símbolos
        """
        self.linked_table = linked_table
        self.symbol_table = symbol_table
        self.table = QuadrupleTable()
        self.current_function = None
        self.param_offset = 0
        
        # Stack para trackear el scope actual en LinkedTable
        self.scope_stack = [linked_table.root]
        self.current_scope_node = linked_table.root
        
        # Índice para saber qué hijo visitar en cada scope
        self.child_index = {}  # scope_id -> próximo índice de hijo

        self.break_stack = []
        self.continue_stack = []

        self._lhs_mode = False

    def _enter_scope(self):
        """Entra al siguiente scope hijo disponible"""
        parent_id = self.current_scope_node.id
        
        # Obtener índice del siguiente hijo a visitar
        child_idx = self.child_index.get(parent_id, 0)
        
        # Verificar que hay hijos disponibles
        if child_idx < len(self.current_scope_node.children):
            next_child = self.current_scope_node.children[child_idx]
            
            # Actualizar índice para la próxima vez
            self.child_index[parent_id] = child_idx + 1
            
            # Cambiar al nuevo scope
            self.current_scope_node = next_child
            self.scope_stack.append(next_child)
        
    def _exit_scope(self):
        """Sale del scope actual"""
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
            self.current_scope_node = self.scope_stack[-1]

    def _get_qualified_name(self, var_name):
        """
        Genera un nombre cualificado para una variable basado en su scope.
        Ejemplo: x en scope 0 -> x_0, x en scope 3 -> x_3
        """
        scope_id = self.current_scope_node.id
        
        # Variables globales (scope 0) no necesitan cualificación
        if scope_id == 0:
            return var_name
        
        # Variables en otros scopes se cualifican con el ID del scope
        return f"{var_name}_{scope_id}"

    # --- Programa principal
    def visitProgram(self, ctx):
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            if hasattr(child, "accept"):
                self.visit(child)
        return None

    # --- Bloque
    def visitBlock(self, ctx):
        """Maneja bloques con scopes"""
        self._enter_scope()
        try:
            for stmt in ctx.statement():
                self.visit(stmt)
        finally:
            self._exit_scope()
        return None

    # --- Declaración de variable: let/var x = expr;
    def visitVariableDeclaration(self, ctx):
        var = ctx.Identifier().getText()
        qualified_var = self._get_qualified_name(var)

        # Si existe inicialización
        if ctx.initializer():
            value = self.visit(ctx.initializer())
            self.table.add("=", value, None, qualified_var)

        return qualified_var

    # --- Declaración de constante: const PI: integer = 314;
    def visitConstantDeclaration(self, ctx):
        const_name = ctx.Identifier().getText()
        qualified_name = self._get_qualified_name(const_name)
        value = self.visit(ctx.expression())

        self.table.add("=", value, None, qualified_name)
        return qualified_name

    # --- Inicializador: = expr
    def visitInitializer(self, ctx):
        return self.visit(ctx.expression())

    # --- Asignación: x = expr;
    def visitAssignment(self, ctx):
        var = ctx.Identifier().getText()
        
        # Buscar en qué scope está definida la variable
        qualified_var = self._find_variable_in_scopes(var)

        expr_node = ctx.expression()
        if isinstance(expr_node, list):
            expr_node = expr_node[0]

        value = self.visit(expr_node)
        self.table.add("=", value, None, qualified_var)
        return qualified_var
    
    def visitAssignmentExpr(self, ctx):
        if ctx.getChildCount() == 3 and ctx.getChild(1).getText() == '=':
            lhs_ctx = ctx.getChild(0)
            rhs_ctx = ctx.getChild(2)

            prev = self._lhs_mode
            self._lhs_mode = True
            lhs_addr = self.visit(lhs_ctx)
            self._lhs_mode = False

            rhs_val  = self.visit(rhs_ctx)

            if isinstance(lhs_addr, dict) and lhs_addr.get("kind") == "index":
                self.table.add("setelem", lhs_addr["base"], lhs_addr["index"], rhs_val)
                return lhs_addr["base"]

            self.table.add("=", rhs_val, None, lhs_addr)
            return lhs_addr
        return self.visitChildren(ctx)

    def _find_variable_in_scopes(self, var_name):
        """
        Busca una variable en el scope actual y sus padres,
        retornando el nombre cualificado correcto.
        """
        # Recorrer desde el scope actual hacia arriba
        current = self.current_scope_node
        while current is not None:
            if var_name in current.symbols:
                # Encontrada! Retornar nombre cualificado
                if current.id == 0:
                    return var_name  # Global
                return f"{var_name}_{current.id}"
            current = current.parent
        
        # No encontrada (error semántico, pero aquí solo retornamos el nombre)
        return var_name

    # --- Print: print(expr);
    def visitPrintStatement(self, ctx):
        value = self.visit(ctx.expression())
        self.table.add("print", value, None, None)
        return None

    # --- Expresiones principales
    def visitExpression(self, ctx):
        return self.visit(ctx.assignmentExpr())

    def visitExprNoAssign(self, ctx):
        return self.visit(ctx.conditionalExpr())

    def visitTernaryExpr(self, ctx):
        return self.visit(ctx.logicalOrExpr())

    # --- Expresiones lógicas con || y &&
    def visitLogicalOrExpr(self, ctx):
        left = self.visit(ctx.logicalAndExpr(0))
        for i in range(1, len(ctx.logicalAndExpr())):
            right = self.visit(ctx.logicalAndExpr(i))
            temp = self.table.new_temp()
            self.table.add("||", left, right, temp)
            left = temp
        return left

    def visitLogicalAndExpr(self, ctx):
        left = self.visit(ctx.equalityExpr(0))
        for i in range(1, len(ctx.equalityExpr())):
            right = self.visit(ctx.equalityExpr(i))
            temp = self.table.new_temp()
            self.table.add("&&", left, right, temp)
            left = temp
        return left

    # --- Expresiones de igualdad == y !=
    def visitEqualityExpr(self, ctx):
        left = self.visit(ctx.relationalExpr(0))
        for i in range(1, len(ctx.relationalExpr())):
            operator = ctx.getChild(2 * i - 1).getText()
            right = self.visit(ctx.relationalExpr(i))
            temp = self.table.new_temp()
            self.table.add(operator, left, right, temp)
            left = temp
        return left

    # --- Expresiones relacionales <, <=, >, >=
    def visitRelationalExpr(self, ctx):
        left = self.visit(ctx.additiveExpr(0))
        for i in range(1, len(ctx.additiveExpr())):
            operator = ctx.getChild(2 * i - 1).getText()
            right = self.visit(ctx.additiveExpr(i))
            temp = self.table.new_temp()
            self.table.add(operator, left, right, temp)
            left = temp
        return left

    # --- Expresiones aditivas: + y -
    def visitAdditiveExpr(self, ctx):
        left = self.visit(ctx.multiplicativeExpr(0))
        for i in range(1, len(ctx.multiplicativeExpr())):
            operator = ctx.getChild(2 * i - 1).getText()
            right = self.visit(ctx.multiplicativeExpr(i))
            temp = self.table.new_temp()
            self.table.add(operator, left, right, temp)
            left = temp
        return left

    # --- Expresiones multiplicativas: *, /, %
    def visitMultiplicativeExpr(self, ctx):
        left = self.visit(ctx.unaryExpr(0))
        for i in range(1, len(ctx.unaryExpr())):
            operator = ctx.getChild(2 * i - 1).getText()
            right = self.visit(ctx.unaryExpr(i))
            temp = self.table.new_temp()
            self.table.add(operator, left, right, temp)
            left = temp
        return left

    # --- Unarios: -, !
    def visitUnaryExpr(self, ctx):
        if ctx.getChildCount() > 1:
            operator = ctx.getChild(0).getText()
            operand = self.visit(ctx.unaryExpr())
            temp = self.table.new_temp()
            if operator == "-":
                self.table.add("neg", operand, None, temp)
            elif operator == "!":
                self.table.add("not", operand, None, temp)
            return temp
        else:
            return self.visit(ctx.primaryExpr())

    # --- Expresiones primarias (literales, identificadores, paréntesis)
    def visitPrimaryExpr(self, ctx):
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        elif ctx.leftHandSide():
            return self.visit(ctx.leftHandSide())
        elif ctx.expression():
            return self.visit(ctx.expression())
        return None

    # --- LITERALES
    def visitLiteralExpr(self, ctx):
        # NUEVO: literal de arreglo
        if hasattr(ctx, "arrayLiteral") and ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())

        if ctx.Literal():
            return ctx.Literal().getText()
        elif ctx.getText() in ["null", "true", "false"]:
            return ctx.getText()
        return ctx.getText()

    # --- LISTAS
    def visitArrayLiteral(self, ctx):
        n = len(ctx.expression())
        temp_arr = self.table.new_temp()
        self.table.add("newarr", n, None, temp_arr)
        for i in range(n):
            val = self.visit(ctx.expression(i))
            self.table.add("setelem", temp_arr, i, val)
        return temp_arr

    def visitLeftHandSide(self, ctx):
        """
        Soporta:
          - llamadas encadenadas base(...)
          - indexación base[expr] (rvalue o lvalue)
        """
        base = self.visit(ctx.primaryAtom())
        suffixes = list(ctx.suffixOp())

        for idx, suffix in enumerate(suffixes):
            first = suffix.getChild(0).getText()

            # Llamada: base(...)
            if first == '(':
                base = self.visitCallExprWithBase(suffix, base)
                continue

            # Indexación: base[expr]
            if first == '[':
                index_val = self.visit(suffix.expression())

                is_last_suffix = (idx == len(suffixes) - 1)
                if self._lhs_mode and is_last_suffix:
                    return {"kind": "index", "base": base, "index": index_val}
                else:
                    t = self.table.new_temp()
                    self.table.add("getelem", base, index_val, t)
                    base = t
                continue

            base = self.visit(suffix)

        return base

    def visitCallExprWithBase(self, ctx, func_name):
        args = []
        if ctx.arguments():
            for expr_ctx in ctx.arguments().expression():
                arg_val = self.visit(expr_ctx)
                args.append(arg_val)
                self.table.add("arg", arg_val, None, None)
        
        temp = self.table.new_temp()
        self.table.add("call", func_name, len(args), temp)
        return temp

    def visitIdentifierExpr(self, ctx):
        var_name = ctx.Identifier().getText()
        return self._find_variable_in_scopes(var_name)

    def visitNewExpr(self, ctx):
        return f"new {ctx.Identifier().getText()}"

    def visitThisExpr(self, ctx):
        return "this"

    def visitChildren(self, node):
        return super().visitChildren(node)
    
    def visitFunctionDeclaration(self, ctx):
        func_name = ctx.Identifier().getText()
        self.current_function = func_name
        
        # Marca inicio de función
        self.table.add("func", None, None, func_name)
        
        # Entrar al scope de la función
        self._enter_scope()
        
        try:
            # Parámetros (están en el scope de la función, no en el bloque)
            if ctx.parameters():
                for param_ctx in ctx.parameters().parameter():
                    param_name = param_ctx.Identifier().getText()
                    qualified_param = self._get_qualified_name(param_name)
                    self.table.add("param", None, None, qualified_param)
            
            # El bloque de la función es un hijo del scope de función
            # No llamamos self.visit(ctx.block()) porque eso crearía otro scope
            # En su lugar, procesamos las declaraciones directamente
            if ctx.block():
                # Entrar al scope del bloque
                self._enter_scope()
                try:
                    for stmt in ctx.block().statement():
                        self.visit(stmt)
                finally:
                    self._exit_scope()
            
            # Marca fin de función
            self.table.add("endfunc", None, None, func_name)
        
        finally:
            self._exit_scope()
            self.current_function = None
        
        return None

    # --- Llamada a función: identifier(args)
    def visitCallExpr(self, ctx):
        func_name = ctx.getChild(0).getText()
        args = []
        if ctx.arguments():
            for expr_ctx in ctx.arguments().expression():
                arg_val = self.visit(expr_ctx)
                args.append(arg_val)
                self.table.add("arg", arg_val, None, None)
        temp = self.table.new_temp()
        self.table.add("call", func_name, len(args), temp)
        return temp

    # --- Return
    def visitReturnStatement(self, ctx):
        value = self.visit(ctx.expression()) if ctx.expression() else None
        self.table.add("return", value, None, None)
        return None
    
    def visitTryCatchStatement(self, ctx):
        # Etiquetas para control de flujo
        start_try = self.table.new_label()
        end_try = self.table.new_label()
        start_catch = self.table.new_label()
        end_catch = self.table.new_label()

        # --- Bloque TRY ---
        self.table.add("label", None, None, start_try)

        # Entrar al scope del bloque try
        self._enter_scope()
        try:
            for stmt in ctx.block(0).statement():
                self.visit(stmt)
        finally:
            self._exit_scope()

        # Saltar al final si no hubo excepción
        self.table.add("goto", None, None, end_catch)

        # --- Bloque CATCH ---
        self.table.add("label", None, None, start_catch)

        # Entrar al scope del catch
        self._enter_scope()
        try:
            # Variable catch (excepción)
            exception_var = ctx.Identifier().getText()
            qualified_exception = self._get_qualified_name(exception_var)
            self.table.add("catch_param", None, None, qualified_exception)

            # Visitamos los statements del bloque catch
            for stmt in ctx.block(1).statement():
                self.visit(stmt)
        finally:
            self._exit_scope()

        # Fin del try/catch
        self.table.add("label", None, None, end_catch)

        return None

    def visitIfStatement(self, ctx):
        cond = self.visit(ctx.expression())
        Lfalse = self.table.new_label()
        Lend = self.table.new_label()

        self.table.add("gotof", cond, None, Lfalse)

        # then
        self.visit(ctx.block(0))

        self.table.add("goto", None, None, Lend)
        self.table.add("label", None, None, Lfalse)

        # else  
        if ctx.block(1):
            self.visit(ctx.block(1))

        self.table.add("label", None, None, Lend)
        return None

    def visitWhileStatement(self, ctx):
        Lstart = self.table.new_label()
        Lend = self.table.new_label()

        # continue vuelve a evaluar la condición
        self.continue_stack.append(Lstart)
        self.break_stack.append(Lend)

        self.table.add("label", None, None, Lstart)

        cond = self.visit(ctx.expression())
        self.table.add("gotof", cond, None, Lend)

        self.visit(ctx.block())

        self.table.add("goto", None, None, Lstart)
        self.table.add("label", None, None, Lend)

        self.continue_stack.pop()
        self.break_stack.pop()
        return None


    def visitDoWhileStatement(self, ctx):
        Lstart = self.table.new_label()
        Lend = self.table.new_label()

        # continue evalua la condición al final
        self.continue_stack.append(Lstart)
        self.break_stack.append(Lend)

        self.table.add("label", None, None, Lstart)
        self.visit(ctx.block())

        cond = self.visit(ctx.expression())
        self.table.add("gotof", cond, None, Lend)
        self.table.add("goto", None, None, Lstart)
        self.table.add("label", None, None, Lend)

        self.continue_stack.pop()
        self.break_stack.pop()
        return None

    def visitForStatement(self, ctx):
        # init
        assigns = ctx.assignment() if hasattr(ctx, "assignment") else None

        if ctx.variableDeclaration():
            self.visit(ctx.variableDeclaration())
        elif assigns:
            if isinstance(assigns, list) and len(assigns) >= 1:
                self.visit(assigns[0])
            elif not isinstance(assigns, list):
                self.visit(assigns)

        Lstart = self.table.new_label()
        Lcont = self.table.new_label()
        Lend = self.table.new_label()

        self.continue_stack.append(Lcont)
        self.break_stack.append(Lend)

        self.table.add("label", None, None, Lstart)

        # cond
        if ctx.expression(0):
            cond = self.visit(ctx.expression(0))
            self.table.add("gotof", cond, None, Lend)

        # cuerpo
        self.visit(ctx.block())

        # incremento
        self.table.add("label", None, None, Lcont)
        inc_done = False
        if assigns:
            if isinstance(assigns, list):
                if ctx.variableDeclaration():
                    self.visit(assigns[-1])
                    inc_done = True
                else:
                    if len(assigns) >= 2:
                        self.visit(assigns[-1])
                        inc_done = True
            else:
                if ctx.variableDeclaration():
                    self.visit(assigns)
                    inc_done = True

        if not inc_done and ctx.expression(1):
            expr2 = ctx.expression(1)
            expr_text = expr2.getText()
            val = self.visit(expr2)

            if self._looks_like_simple_assignment(expr_text):
                lhs = expr_text.split('=', 1)[0].strip()
                if lhs:
                    qlhs = self._find_variable_in_scopes(lhs)
                    self.table.add("=", val, None, qlhs)


        self.table.add("goto", None, None, Lstart)
        self.table.add("label", None, None, Lend)

        self.continue_stack.pop()
        self.break_stack.pop()
        return None

    def _looks_like_simple_assignment(self, text: str) -> bool:
        if not text:
            return False
        for bad in ("==", ">=", "<=", "!="):
            if bad in text:
                return False
        return "=" in text

    def visitBreakStatement(self, ctx):
        target = self.break_stack[-1]
        self.table.add("goto", None, None, target)
        return None

    def visitContinueStatement(self, ctx):
        target = self.continue_stack[-1]
        self.table.add("goto", None, None, target)
        return None

    def visitSwitchStatement(self, ctx):
        discr = self.visit(ctx.expression())
        Lend = self.table.new_label()

        # Preparar labels por case
        case_labels = []
        for _ in ctx.switchCase():
            case_labels.append(self.table.new_label())

        Ldefault = self.table.new_label() if ctx.defaultCase() else Lend

        for i, case_ctx in enumerate(ctx.switchCase()):
            case_val = self.visit(case_ctx.expression())
            tcmp = self.table.new_temp()
            self.table.add("==", discr, case_val, tcmp)
            Lnext = self.table.new_label()
            self.table.add("gotof", tcmp, None, Lnext)
            self.table.add("goto", None, None, case_labels[i])
            self.table.add("label", None, None, Lnext)

        self.table.add("goto", None, None, Ldefault)

        for i, case_ctx in enumerate(ctx.switchCase()):
            self.table.add("label", None, None, case_labels[i])
            for st in case_ctx.statement():
                self.visit(st)
            self.table.add("goto", None, None, Lend)

        if ctx.defaultCase():
            self.table.add("label", None, None, Ldefault)
            for st in ctx.defaultCase().statement():
                self.visit(st)

        self.table.add("label", None, None, Lend)
        return None
