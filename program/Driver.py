import sys
from antlr4 import *
from MiniLangLexer import MiniLangLexer
from MiniLangParser import MiniLangParser
from MiniLangListener import MiniLangListener  # Listener generado por ANTLR

class EvalListener(MiniLangListener):
    def __init__(self):
        self.vars = {}

    def exitAssign(self, ctx):
        var_name = ctx.ID().getText()
        value = self.evalExpr(ctx.expr())
        self.vars[var_name] = value

    def exitPrintExpr(self, ctx):
        value = self.evalExpr(ctx.expr())
        print(value)

    def evalExpr(self, ctx):
        from MiniLangParser import MiniLangParser

        if isinstance(ctx, MiniLangParser.IntContext):
            return int(ctx.INT().getText())

        elif isinstance(ctx, MiniLangParser.IdContext):
            var_name = ctx.ID().getText()
            return self.vars.get(var_name, 0)

        elif isinstance(ctx, MiniLangParser.ParensContext):
            return self.evalExpr(ctx.expr())

        elif isinstance(ctx, MiniLangParser.MulDivContext):
            left = self.evalExpr(ctx.expr(0))
            right = self.evalExpr(ctx.expr(1))
            if ctx.MUL():
                return left * right
            else:
                return left // right  # División entera

        elif isinstance(ctx, MiniLangParser.AddSubContext):
            left = self.evalExpr(ctx.expr(0))
            right = self.evalExpr(ctx.expr(1))
            if ctx.ADD():
                return left + right
            else:
                return left - right

        else:
            return 0

def main(argv):
    input_stream = FileStream(argv[1])
    lexer = MiniLangLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = MiniLangParser(stream)
    tree = parser.prog()

    from antlr4.tree.Tree import ParseTreeWalker
    walker = ParseTreeWalker()
    listener = EvalListener()
    walker.walk(listener, tree)

if __name__ == '__main__':
    main(sys.argv)
