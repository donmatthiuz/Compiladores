import sys
from antlr4 import *    
from CompiScriptLexer import CompiScriptLexer
from CompiScriptParser import CompiScriptParser
from type_check_visitor import TypeCheckVisitor

def main(argv):
    input_stream = FileStream(argv[1])
    lexer = CompiScriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiScriptParser(stream)
    tree = parser.program()

    visitor = TypeCheckVisitor()
    try:
        visitor.visit(tree)
        print("Type checking passed")
    except TypeError as e:
        print(f"Type checking error: {e}")

if __name__ == '__main__':
    main(sys.argv)
