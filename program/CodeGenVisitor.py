from CompiScriptVisitor import CompiScriptVisitor
from QuadrupleTable import QuadrupleTable

class CodeGenVisitor(CompiScriptVisitor):
    def __init__(self):
        self.table = QuadrupleTable()

    # --- Declaración de variable: let x = expr;
    def visitVarDeclaration(self, ctx):
        var = ctx.Identifier().getText()
        value = self.visit(ctx.expression())
        self.table.add("=", value, None, var)
        return var

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

    # --- Expresiones aditivas: expr + expr
    def visitAdditiveExpr(self, ctx):
        left = self.visit(ctx.multiplicativeExpr(0))
        if len(ctx.multiplicativeExpr()) > 1:
            right = self.visit(ctx.multiplicativeExpr(1))
            temp = self.table.new_temp()
            self.table.add("+", left, right, temp)
            return temp
        else:
            # Solo un operando, no hay suma
            return left


    # --- Expresiones multiplicativas: expr * expr
    def visitMultiplicativeExpr(self, ctx):
        left = self.visit(ctx.unaryExpr(0))
        if len(ctx.unaryExpr()) > 1:
            right = self.visit(ctx.unaryExpr(1))
            temp = self.table.new_temp()
            self.table.add("*", left, right, temp)
            return temp
        else:
            return left


    # --- Literales: números
    def visitLiteralExpr(self, ctx):
        return ctx.getText()

    # --- Identificadores: variables
    def visitIdentifierExpr(self, ctx):
        return ctx.Identifier().getText()
