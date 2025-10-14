from CompiScriptVisitor import CompiScriptVisitor
from QuadrupleTable import QuadrupleTable

class CodeGenVisitor(CompiScriptVisitor):
    def __init__(self, table):
        self.table_symbols = table
        self.table = QuadrupleTable()

    # --- Programa principal
    def visitProgram(self, ctx):
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            if hasattr(child, "accept"):
                self.visit(child)
        return None

    # --- Declaración de variable: let/var x = expr;
    def visitVariableDeclaration(self, ctx):
        var = ctx.Identifier().getText()

        # Si existe inicialización
        if ctx.initializer():
            value = self.visit(ctx.initializer())
            self.table.add("=", value, None, var)

        # Si tiene anotación de tipo, podrías guardarla en la tabla de símbolos
        if ctx.typeAnnotation():
            type_ = ctx.typeAnnotation().getText().replace(":", "").strip()
            sym = self.table_symbols.lookup(var)
            if sym:
                sym.type_ = type_

        return var

    # --- Declaración de constante: const PI: integer = 314;
    def visitConstantDeclaration(self, ctx):
        const_name = ctx.Identifier().getText()
        value = self.visit(ctx.expression())

        self.table.add("=", value, None, const_name)

        # Anotar tipo si lo tiene
        if ctx.typeAnnotation():
            type_ = ctx.typeAnnotation().getText().replace(":", "").strip()
            sym = self.table_symbols.lookup(const_name)
            if sym:
                sym.type_ = type_

        return const_name

    # --- Inicializador: = expr
    def visitInitializer(self, ctx):
        return self.visit(ctx.expression())

    # --- Asignación: x = expr;
    def visitAssignment(self, ctx):
        var = ctx.Identifier().getText()
        value = self.visit(ctx.expression())
        self.table.add("=", value, None, var)
        return var

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
        # No implementamos operador ternario aún
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
            return self.visit(ctx.expression())  # (expr)
        return None

    def visitLiteralExpr(self, ctx):
        if ctx.Literal():
            return ctx.Literal().getText()
        elif ctx.getText() in ["null", "true", "false"]:
            return ctx.getText()
        return ctx.getText()

    def visitLeftHandSide(self, ctx):
        return self.visit(ctx.primaryAtom())

    def visitIdentifierExpr(self, ctx):
        return ctx.Identifier().getText()

    def visitNewExpr(self, ctx):
        return f"new {ctx.Identifier().getText()}"

    def visitThisExpr(self, ctx):
        return "this"

    def visitChildren(self, node):
        return super().visitChildren(node)
