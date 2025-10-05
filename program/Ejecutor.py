import sys
from antlr4 import *    
from CompiScriptLexer import CompiScriptLexer
from CompiScriptParser import CompiScriptParser
from type_check_visitor import TypeCheckVisitor
from CodeGenVisitor import CodeGenVisitor

def main(argv):
    
    input_stream = FileStream(argv[1], encoding='utf-8')
    lexer = CompiScriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiScriptParser(stream)
    tree = parser.program()

    visitor = TypeCheckVisitor()
    try:
        visitor.visit(tree)
        
        codegen = CodeGenVisitor()
        codegen.visit(tree)
        codegen.table.display()
        return
    except (TypeError, NameError, SyntaxError) as e:
        print(f"{e}")
        sys.exit(1)
    

if __name__ == '__main__':
    main(sys.argv)
