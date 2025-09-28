from CompiScriptVisitor import CompiScriptVisitor
from QuadrupleTable import QuadrupleTable

class CodeGenVisitor(CompiScriptVisitor):
    def __init__(self):
        self.table = QuadrupleTable()
    
    # --- Programa principal
    def visitProgram(self, ctx):
        """Visita todas las declaraciones del programa"""
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            if hasattr(child, 'accept'):
                self.visit(child)
        return None
    
    # --- Declaración de variable: let/var x = expr;
    def visitVariableDeclaration(self, ctx):
        var = ctx.Identifier().getText()
        
        if ctx.initializer():
            value = self.visit(ctx.initializer())
            self.table.add("=", value, None, var)
        
        return var
    
    # --- Declaración de constante: const x = expr;
    def visitConstantDeclaration(self, ctx):
        var = ctx.Identifier().getText()
        value = self.visit(ctx.expression())
        self.table.add("=", value, None, var)
        return var
    
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
    
    # --- Expresiones
    def visitExpression(self, ctx):
        return self.visit(ctx.assignmentExpr())
    
    def visitExprNoAssign(self, ctx):
        return self.visit(ctx.conditionalExpr())
    
    def visitTernaryExpr(self, ctx):
        # Por simplicidad, solo manejamos el caso sin operador ternario
        return self.visit(ctx.logicalOrExpr())
    
    def visitLogicalOrExpr(self, ctx):
        # Tomar el primer hijo por simplicidad
        return self.visit(ctx.logicalAndExpr(0))
    
    def visitLogicalAndExpr(self, ctx):
        return self.visit(ctx.equalityExpr(0))
    
    def visitEqualityExpr(self, ctx):
        return self.visit(ctx.relationalExpr(0))
    
    def visitRelationalExpr(self, ctx):
        return self.visit(ctx.additiveExpr(0))
    
    # --- Expresiones aritméticas
    def visitAdditiveExpr(self, ctx):
        left = self.visit(ctx.multiplicativeExpr(0))
        
        # Si hay más de un multiplicativeExpr, hay operación
        if len(ctx.multiplicativeExpr()) > 1:
            # Buscar el operador
            operator = "+"
            for i in range(ctx.getChildCount()):
                child = ctx.getChild(i)
                if hasattr(child, 'getText'):
                    text = child.getText()
                    if text in ['+', '-']:
                        operator = text
                        break
            
            right = self.visit(ctx.multiplicativeExpr(1))
            temp = self.table.new_temp()
            self.table.add(operator, left, right, temp)
            return temp
        else:
            return left
    
    def visitMultiplicativeExpr(self, ctx):
        left = self.visit(ctx.unaryExpr(0))
        
        if len(ctx.unaryExpr()) > 1:
            # Buscar el operador
            operator = "*"
            for i in range(ctx.getChildCount()):
                child = ctx.getChild(i)
                if hasattr(child, 'getText'):
                    text = child.getText()
                    if text in ['*', '/', '%']:
                        operator = text
                        break
            
            right = self.visit(ctx.unaryExpr(1))
            temp = self.table.new_temp()
            self.table.add(operator, left, right, temp)
            return temp
        else:
            return left
    
    def visitUnaryExpr(self, ctx):
        # Si tiene operador unario (-, !)
        if ctx.getChildCount() > 1:
            operator = ctx.getChild(0).getText()
            operand = self.visit(ctx.unaryExpr())
            
            if operator == "-":
                temp = self.table.new_temp()
                self.table.add("neg", operand, None, temp)
                return temp
            elif operator == "!":
                temp = self.table.new_temp()
                self.table.add("not", operand, None, temp)
                return temp
        else:
            return self.visit(ctx.primaryExpr())
    
    def visitPrimaryExpr(self, ctx):
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        elif ctx.leftHandSide():
            return self.visit(ctx.leftHandSide())
        elif ctx.expression():  # expresión entre paréntesis
            return self.visit(ctx.expression())
        
        return None
    
    def visitLiteralExpr(self, ctx):
        if ctx.Literal():
            return ctx.Literal().getText()
        elif ctx.getText() in ['null', 'true', 'false']:
            return ctx.getText()
        
        return ctx.getText()
    
    def visitLeftHandSide(self, ctx):
        # leftHandSide tiene primaryAtom y posibles suffixOp
        return self.visit(ctx.primaryAtom())
    
    def visitIdentifierExpr(self, ctx):
        return ctx.Identifier().getText()
    
    def visitNewExpr(self, ctx):
        return f"new {ctx.Identifier().getText()}"
    
    def visitThisExpr(self, ctx):
        return "this"
    
    # --- Método genérico para casos no manejados
    def visitChildren(self, node):
        return super().visitChildren(node)