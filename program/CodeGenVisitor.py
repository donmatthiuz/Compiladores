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
        self._last_index_access = None


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
        self._last_index_access = None
        
        # Verificar si tiene un '.' en los hijos
        has_dot = False
        for i in range(ctx.getChildCount()):
            if ctx.getChild(i).getText() == '.':
                has_dot = True
                break
        
        if has_dot:
            # Property assignment: expression '.' Identifier '=' expression ';'
            
            # Primer hijo es la expression (this)
            lhs_expr = ctx.expression(0)  # this
            prev = self._lhs_mode
            self._lhs_mode = True
            base = self.visit(lhs_expr)
            self._lhs_mode = prev
            
            # Después del '.' viene el Identifier
            attr_name = ctx.Identifier().getText()  # nombre
            
            # Después del '=' viene la segunda expression
            rhs_val = self.visit(ctx.expression(1))  # nombre_2
            
            
            if isinstance(base, str) and base.startswith("this"):
                resolved_attr = self._resolve_this_attribute(attr_name)
                if resolved_attr:
                    self.table.add("setattr", base, resolved_attr, rhs_val)
                    return base
            

            self.table.add("setattr", base, attr_name, rhs_val)
            return base

        
        else:
            # Simple assignment: Identifier '=' expression ';'
            var_name = ctx.Identifier().getText()
            qualified_var = self._find_variable_in_scopes(var_name)
            rhs_val = self.visit(ctx.expression(0))
            
            self.table.add("=", rhs_val, None, qualified_var)
            return qualified_var   
    
    def visitAssignmentExpr(self, ctx):
        txt = ctx.getText()
        is_assign = ('=' in txt) and not any(op in txt for op in ('==', '!=', '<=', '>='))
        if not is_assign:
            return self.visitChildren(ctx)

        rhs_ctx = ctx.getChild(ctx.getChildCount() - 1)
        rhs_val = self.visit(rhs_ctx)

        prev = self._lhs_mode
        self._lhs_mode = True
        lhs_ctx = ctx.getChild(0)
        lhs_addr = self.visit(lhs_ctx)
        self._lhs_mode = prev

        # --- Emisión para atributos
        if isinstance(lhs_addr, dict) and lhs_addr.get("kind") == "attr":
            self.table.add("setattr", lhs_addr["base"], lhs_addr["attr"], rhs_val)
            return lhs_addr["base"]

        # --- Emisión para índices
        if isinstance(lhs_addr, dict) and lhs_addr.get("kind") == "index":
            self.table.add("setelem", lhs_addr["base"], lhs_addr["index"], rhs_val)
            return lhs_addr["base"]

        if isinstance(lhs_addr, str):
            base, index = self._last_getelem_sources(lhs_addr)
            if base is None:
                base, index = self._last_getelem_with_base(lhs_addr)
            if base is None:
                base, index = self._last_getelem_any()
            if base is not None:
                self.table.add("setelem", base, index, rhs_val)
                return base
            self.table.add("=", rhs_val, None, lhs_addr)
            return lhs_addr

        base, index = self._last_getelem_any()
        if base is not None:
            self.table.add("setelem", base, index, rhs_val)
            return base

        self.table.add("=", rhs_val, None, lhs_addr)
        return lhs_addr

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

    def _compute_offset(self, base, index):
        """
        Emite un cuádruplo para calcular el desplazamiento (offset)
        de un elemento dentro de una estructura indexada.
        """
        temp_offset = self.table.new_temp()
        self.table.add("offset", base, index, temp_offset)
        return temp_offset


    def visitClassDeclaration(self, ctx):
        class_name = ctx.Identifier(0).getText()

        # Marca inicio de clase en la tabla intermedia
        self.table.add("class", None, None, class_name)

        # Entrar al scope de la clase
        self._enter_scope()
        try:
            # Recorremos los miembros de la clase
            for member in ctx.classMember():

                # --- Atributos (variable o constante)
                if hasattr(member, "variableDeclaration") and member.variableDeclaration():
                    vctx = member.variableDeclaration()
                    field_name = vctx.Identifier().getText()
                    qualified = self._get_qualified_name(field_name)

                    self.table.add("attr", None, None, qualified)

                    if vctx.initializer():
                        val = self.visit(vctx.initializer())
                        self.table.add("=", val, None, qualified)

                    # Registrar en linked table
                    self.current_scope_node.add_symbol(field_name, None)

                elif hasattr(member, "constantDeclaration") and member.constantDeclaration():
                    cctx = member.constantDeclaration()
                    field_name = cctx.Identifier().getText()
                    qualified = self._get_qualified_name(field_name)

                    self.table.add("attr", None, None, qualified)
                    val = self.visit(cctx.expression())
                    self.table.add("=", val, None, qualified)

                    self.current_scope_node.add_symbol(field_name, None)

                # --- Métodos
                elif hasattr(member, "functionDeclaration") and member.functionDeclaration():
                    fctx = member.functionDeclaration()
                    method_name = fctx.Identifier().getText()
                    full_name = f"{class_name}.{method_name}"
                    self.table.add("func", None, None, full_name)

                    # Entrar al scope del método
                    self._enter_scope()
                    try:
                        # Insertar 'this' como primer parámetro
                        this_qualified = self._get_qualified_name("this")
                        self.table.add("param", None, None, this_qualified)
                        self.current_scope_node.add_symbol("this", class_name)

                        # Registrar parámetros del método
                        if fctx.parameters():
                            for param_ctx in fctx.parameters().parameter():
                                pname = param_ctx.Identifier().getText()
                                pqual = self._get_qualified_name(pname)
                                self.table.add("param", None, None, pqual)
                                self.current_scope_node.add_symbol(pname, None)

                        # Bloque de la función (scope hijo)
                        if fctx.block():
                            self._enter_scope()
                            try:
                                for stmt in fctx.block().statement():
                                    self.visit(stmt)
                            finally:
                                self._exit_scope()

                        self.table.add("endfunc", None, None, full_name)
                    finally:
                        self._exit_scope()
        finally:
            self._exit_scope()
            self.table.add("endclass", None, None, class_name)

        return None

    
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


    def _resolve_this_attribute(self, attr_name):
        """
        Resuelve this.attr al nombre cualificado del atributo en el scope de clase.
        Navega desde el scope actual hasta encontrar el scope de clase.
        """
        current = self.current_scope_node
        
        
        # Navegar hacia arriba hasta encontrar el scope de clase
        while current is not None:
            
            if current.context_type == "class":
                # Encontramos el scope de clase, buscar el atributo
                if attr_name in current.symbols:
                    resolved = f"{attr_name}_{current.id}"
                    return resolved
                else:
                    continue
                break
            current = current.parent
        
        return None
    
    
    def _get_object_type(self, obj_var):
        if not isinstance(obj_var, str):
            return None
        
        # Extraer nombre base
        base_name = obj_var.split('_')[0] if '_' in obj_var else obj_var
        
        # Buscar en scopes
        current = self.current_scope_node
        while current is not None:
            if obj_var in current.symbols:
                return current.symbols[obj_var]
            elif base_name in current.symbols:
                return current.symbols[base_name]
            current = current.parent
        
        return None
    
    def visitLeftHandSide(self, ctx):
        base = self.visit(ctx.primaryAtom())
        suffixes = list(ctx.suffixOp())

        for idx, suffix in enumerate(suffixes):
            first = suffix.getChild(0).getText()

            # Llamada: base(...)
            if first == '(':
                # 🔥 NUEVO: Verificar si el suffix anterior fue un acceso a método
                if idx > 0:
                    prev_suffix = suffixes[idx - 1]
                    if prev_suffix.getChild(0).getText() == '.':
                        # Es una llamada a método: objeto.metodo()
                        method_name = prev_suffix.Identifier().getText()
                        
                        # Obtener el tipo del objeto base (antes del método)
                        # Necesitamos el base ANTES de procesar el '.'
                        # Para esto, debemos reconstruir o guardar el base anterior
                        
                        # Solución: detectar y manejar llamadas a método de forma especial
                        pass
                
                base = self.visitCallExprWithBase(suffix, base)
                continue

            # Indexación: base[expr]
            if first == '[':
                index_val = self.visit(suffix.expression())
                self._last_index_access = (base, index_val)

                is_last_suffix = (idx == len(suffixes) - 1)
                if self._lhs_mode and is_last_suffix:
                    return {"kind": "index", "base": base, "index": index_val}
                else:
                    t = self.table.new_temp()
                    offset_temp = self._compute_offset(base, index_val)
                    self.table.add("getelem", base, offset_temp, t)
                    base = t
                continue

            # Acceso a atributo: .identifier
            if first == '.':
                attr_name = suffix.Identifier().getText()
                is_last_suffix = (idx == len(suffixes) - 1)
                
                # 🔥 CRÍTICO: Verificar si el SIGUIENTE suffix es una llamada
                is_method_call = False
                if idx + 1 < len(suffixes):
                    next_suffix = suffixes[idx + 1]
                    if next_suffix.getChild(0).getText() == '(':
                        is_method_call = True
                
                if is_method_call:
                    # Es una llamada a método, no generar getattr
                    # Solo construir el nombre completo del método
                    obj_type = self._get_object_type(base)
                    if obj_type:
                        base = f"{obj_type}.{attr_name}"
                    else:
                        base = attr_name
                    continue
                
                # Manejar this.atributo
                if isinstance(base, str) and base.startswith("this"):
                    resolved = self._resolve_this_attribute(attr_name)
                    if resolved:
                        if self._lhs_mode and is_last_suffix:
                            return resolved
                        temp = self.table.new_temp()
                        self.table.add("getattr", base, resolved, temp)
                        base = temp
                        continue
                
                # Para cualquier otro objeto (acceso a atributo, NO método)
                resolved_attr = self._resolve_attribute_from_object(base, attr_name)
                
                if self._lhs_mode and is_last_suffix:
                    return {"kind": "attr", "base": base, "attr": resolved_attr or attr_name}
                else:
                    temp = self.table.new_temp()
                    self.table.add("getattr", base, resolved_attr or attr_name, temp)
                    base = temp
                continue
                
            base = self.visit(suffix)

        return base
    
    def _resolve_attribute_from_object(self, obj_var, attr_name):
        """
        Resuelve el nombre cualificado de un atributo basándose en el tipo del objeto.
        """
        # 1. Buscar el tipo de la variable en los scopes
        obj_type = None
        current = self.current_scope_node
        
        # Extraer nombre base (sin cualificación)
        base_name = obj_var.split('_')[0] if '_' in obj_var else obj_var
        
        while current is not None:
            # Probar primero con el nombre exacto (puede ser cualificado)
            if obj_var in current.symbols:
                obj_type = current.symbols[obj_var]
                break
            # Probar con el nombre base (sin cualificar)
            elif base_name in current.symbols:
                obj_type = current.symbols[base_name]
                break
            current = current.parent
        
        # 2. Si encontramos el tipo, buscar el atributo en la clase
        if obj_type:
            # Buscar el scope de la clase en los hijos del root
            for child in self.linked_table.root.children:
                if child.context_type == "class" and child.context_name == obj_type:
                    # Encontramos el scope de la clase
                    if attr_name in child.symbols:
                        # Retornar nombre cualificado del atributo
                        return f"{attr_name}_{child.id}"
        
        # 3. Fallback: si no se pudo resolver, retornar None
        return None
    
    def _resolve_attribute_for_any_object(self, obj_name, attr_name):

        # Buscar el tipo del objeto en los símbolos
        current = self.current_scope_node
        while current is not None:
            if obj_name in current.symbols:
                class_type = current.symbols[obj_name]
                # Buscar la clase en el scope global
                if class_type and self.linked_table.root.symbols.get(class_type):
                    # Buscar el scope de la clase
                    for child in self.linked_table.root.children:
                        if child.context_type == "class" and child.context_name == class_type:
                            if attr_name in child.symbols:
                                return f"{attr_name}_{child.id}"
                break
            current = current.parent
        
        return None
    def visitNewExpr(self, ctx):
        class_name = ctx.Identifier().getText()
        
        temp_obj = self.table.new_temp()
        self.table.add("new", class_name, None, temp_obj)
        

        if ctx.arguments():
            # Pasar el objeto como primer argumento (this)
            self.table.add("arg", temp_obj, None, None)
            
            # Pasar los demás argumentos
            for expr_ctx in ctx.arguments().expression():
                arg_val = self.visit(expr_ctx)
                self.table.add("arg", arg_val, None, None)
            
            # Llamar al constructor
            constructor_name = f"{class_name}.constructor"
            self.table.add("call", constructor_name, len(ctx.arguments().expression()) + 1, None)
        
        return temp_obj
    
    def visitCallExprWithBase(self, ctx, func_name):
        """
        Maneja llamadas a funciones/métodos.
        func_name puede ser:
        - Un nombre simple: "foo"
        - Un nombre de método completo: "Animal.hablar"
        - Un nombre de método con objeto: guardado en self._pending_method_call
        """
        args = []
        
        # Si func_name es un método completo (ej: "Animal.hablar")
        # necesitamos pasar el objeto como primer argumento
        if '.' in func_name and not func_name.startswith('this'):
            # Es una llamada a método de un objeto, pero necesitamos el objeto
            # Este caso se maneja desde visitLeftHandSide con contexto adicional
            pass
        
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
        # Buscar en scopes ascendentes
        qname = self._find_variable_in_scopes(var_name)
        return qname


    def visitNewExpr(self, ctx):
        class_name = ctx.Identifier().getText()
        
        # Crear nueva instancia
        temp_obj = self.table.new_temp()
        self.table.add("new", class_name, None, temp_obj)
        
        # Si hay argumentos, llamar al constructor
        if ctx.arguments():
            # Pasar el objeto como primer argumento (this)
            self.table.add("arg", temp_obj, None, None)
            
            # Pasar los demás argumentos
            for expr_ctx in ctx.arguments().expression():
                arg_val = self.visit(expr_ctx)
                self.table.add("arg", arg_val, None, None)
            
            # Llamar al constructor
            constructor_name = f"{class_name}.constructor"
            num_args = len(ctx.arguments().expression()) + 1  # +1 por this
            self.table.add("call", constructor_name, num_args, None)
        
        return temp_obj

    def visitThisExpr(self, ctx):
        # Buscar "this" en los scopes actuales
        return self._find_variable_in_scopes("this")

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


    def _last_getelem_sources(self, temp_name):
        for op, op1, op2, res in reversed(self.table.quadruples):
            if res == temp_name and op == "getelem":
                return op1, op2
        return None, None

    def _last_getelem_with_base(self, base_name):
        for op, op1, op2, res in reversed(self.table.quadruples):
            if op == "getelem" and op1 == base_name:
                return op1, op2
        return None, None

    def _last_getelem_any(self):
        for op, op1, op2, res in reversed(self.table.quadruples):
            if op == "getelem":
                return op1, op2
        return None, None
    
    def _handle_index_assignment(self, ctx):
        prev = self._lhs_mode
        self._lhs_mode = True
        lhs_node = None
        if hasattr(ctx, "leftHandSide") and ctx.leftHandSide():
            lhs_node = ctx.leftHandSide()
        elif ctx.getChildCount() >= 1:
            lhs_node = ctx.getChild(0)
        lhs_addr = self.visit(lhs_node) if lhs_node is not None else None
        self._lhs_mode = False

        rhs_node = None
        if hasattr(ctx, "expression") and ctx.expression():
            ex = ctx.expression()
            if isinstance(ex, list) or hasattr(ex, "__len__"):
                rhs_node = ex[-1]
            else:
                rhs_node = ex
        else:
            if ctx.getChildCount() >= 3:
                rhs_node = ctx.getChild(ctx.getChildCount() - 1)
        rhs_val = self.visit(rhs_node) if rhs_node is not None else None

        if isinstance(lhs_addr, dict) and lhs_addr.get("kind") == "index":
            self.table.add("setelem", lhs_addr["base"], lhs_addr["index"], rhs_val)
            return lhs_addr["base"]

        if isinstance(lhs_addr, str):
            base, index = self._last_getelem_sources(lhs_addr)
            if base is None:
                base, index = self._last_getelem_with_base(lhs_addr)
            if base is None:
                base, index = self._last_getelem_any()
            if base is not None:
                self.table.add("setelem", base, index, rhs_val)
                return base
            self.table.add("=", rhs_val, None, lhs_addr)
            return lhs_addr

        base, index = self._last_getelem_any()
        if base is not None:
            self.table.add("setelem", base, index, rhs_val)
            return base

        return None

    def visitIndexAssignment(self, ctx):
        return self._handle_index_assignment(ctx)

    def visitIndexAssign(self, ctx):
        return self._handle_index_assignment(ctx)

    def visitArrayIndexAssignment(self, ctx):
        return self._handle_index_assignment(ctx)

    def visitArraySet(self, ctx):
        return self._handle_index_assignment(ctx)

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
