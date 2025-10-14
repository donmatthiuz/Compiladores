import sys
from antlr4 import *    
from CompiScriptLexer import CompiScriptLexer
from CompiScriptParser import CompiScriptParser
from type_check_visitor import TypeCheckVisitor
from CodeGenVisitor import CodeGenVisitor

def main(argv):
    if len(argv) < 2:
        print("Uso: python Driver.py <archivo.cps> [debug|runner]")
        sys.exit(1)

    filename = argv[1]
    mode = argv[2].lower() if len(argv) > 2 else "debug"

    input_stream = FileStream(filename, encoding='utf-8')
    lexer = CompiScriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiScriptParser(stream)
    tree = parser.program()

    # Type checking siempre
    visitor = TypeCheckVisitor()
    
    try:
        visitor.visit(tree)
    except (TypeError, NameError, SyntaxError) as e:
        print(f"{e}")
        sys.exit(1)

    # Solo si es runner, generar código
    if mode == "runner":

        codegen = CodeGenVisitor(visitor.symbol_table)
        codegen.visit(tree)
        codegen.table.display()  # o cualquier acción que quieras ejecutar
    else:
        # debug: solo type check
        print("Debug mode: type checking completed successfully")

if __name__ == '__main__':
    main(sys.argv)
