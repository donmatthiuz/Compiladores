import sys, subprocess, pathlib, textwrap, re, tempfile

HERE = pathlib.Path(__file__).resolve().parent
DRIVER = HERE / "Driver.py"

KNOWN_OPS = {
    "+", "-", "*", "/", "=",
    "<", ">", "<=", ">=", "==", "!=",
    "print", "PRINT",
    "goto", "GOTO",
    "gotof", "GOTOF",
    "label", "LABEL",
    # try/catch
    "catch_param", "CATCH_PARAM",
    "try", "TRY",
    "catch", "CATCH",
    # listas / arreglos
    "newarr", "NEWARR",
    "setelem", "SETELEM",
    "getelem", "GETELEM",
    "offset", "OFFSET",
    # clases / objetos
    "class", "CLASS",
    "endclass", "ENDCLASS",
    "attr", "ATTR",
    "getattr", "GETATTR",
    "setattr", "SETATTR",
    # funciones
    "func", "FUNC",
    "endfunc", "ENDFUNC",
    "param", "PARAM",
    "arg", "ARG",
    "call", "CALL",
    "return", "RETURN",
}

def extract_quads_from_text(text: str):
    quads = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        tokens = re.findall(r"[A-Za-z_<>!=]+|[+\-*/]", stripped)
        if not tokens:
            continue

        op_found = None
        for tok in tokens:
            if tok in KNOWN_OPS:
                op_found = tok
                break

        if op_found is None:
            continue

        quads.append((op_found, "", "", ""))

    return quads

def parse_quads(stdout: str):
    quad_file = HERE / "quadruples.txt"
    if quad_file.exists():
        try:
            text = quad_file.read_text(encoding="utf-8")
            quads = extract_quads_from_text(text)
            if quads:
                return quads
        except Exception as e:
            print(f"[WARN] No se pudo leer quadruples.txt: {e}", file=sys.stderr)

    quads = extract_quads_from_text(stdout)
    return quads

def ops(quads):
    """
    Devuelve la lista de operadores
    """
    return [q[0] for q in quads]

def ops_lower(quads):
    """
    Operadores en minúsculas
    """
    return [q[0].lower() for q in quads]

def find_indices(quads, op):
    return [i for i, q in enumerate(quads) if q[0] == op]

def subseq_in_order(sequence, pattern):
    """
    Verifica que todos los elementos de pattern aparezcan en sequencia
    """
    it = iter(sequence)
    return all(any(x == y for x in it) for y in pattern)

def run_driver(code: str):
    """
    Escribe a un archivo temporal .cps, ejecuta Driver.py en modo 'runner'
    """
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        src = td / "tmp.cps"
        src.write_text(code + "\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(DRIVER), str(src), "runner"],
            capture_output=True, text=True, cwd=HERE
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

# ------------------ TEST CASES ------------------
TESTS = [

# ------------------------------------------------------------
# ARITMÉTICA BÁSICA
# ------------------------------------------------------------
{
    "name": "arithmetic_basic_precedence",
    "code": textwrap.dedent("""\
        let a: integer = 5 + 2 * 3 - 1;
        print(a);
    """),

    "check": lambda q: all(
        op in ops_lower(q)
        for op in ["+", "*", "-", "=", "print"]
    )
},

{
    "name": "arithmetic_with_division",
    "code": textwrap.dedent("""\
        let b: integer = 20 / 2 + 3;
        print(b);
    """),
    "check": lambda q: all(
        op in ops_lower(q)
        for op in ["/", "+", "=", "print"]
    )
},

{
    "name": "arithmetic_multiple_assignments",
    "code": textwrap.dedent("""\
        let x: integer = 1 + 2;
        let y: integer = x * 3;
        let z: integer = y - 4 / 2;
        print(z);
    """),
    "check": lambda q: (
        all(op in ops_lower(q) for op in ["+", "*", "-", "/"]) and
        "print" in ops_lower(q)
    )
},

# ------------------------------------------------------------
# OPERADORES RELACIONALES
# ------------------------------------------------------------
{
    "name": "relational_operators_all",
    "code": textwrap.dedent("""\
        let a: integer = 1;
        let b: integer = 2;

        let r1: boolean = a < b;
        let r2: boolean = a > b;
        let r3: boolean = a <= b;
        let r4: boolean = a >= b;
        let r5: boolean = a == b;
        let r6: boolean = a != b;

        print(r1);
        print(r2);
        print(r3);
        print(r4);
        print(r5);
        print(r6);
    """),
    "check": lambda q: all(
        op in ops(q)
        for op in ["<", ">", "<=", ">=", "==", "!="]
    )
},

# ------------------------------------------------------------
# CONTROL DE FLUJO: IF / ELSE
# ------------------------------------------------------------
{
    "name": "if_else_basic",
    "code": textwrap.dedent("""\
        let x: integer = 0;
        if (x == 0) {
            print(1);
        } else {
            print(2);
        }
    """),
    "check": lambda q: (
        "==" in ops_lower(q) and
        "gotof" in ops_lower(q) and
        "goto" in ops_lower(q) and
        ops_lower(q).count("label") >= 2 and
        "print" in ops_lower(q)
    )
},

# ------------------------------------------------------------
# CONTROL DE FLUJO: WHILE
# ------------------------------------------------------------
{
    "name": "while_loop_increment",
    "code": textwrap.dedent("""\
        let i: integer = 0;
        while (i < 3) {
            i = i + 1;
            print(i);
        }
    """),
    "check": lambda q: all(
        op in ops_lower(q)
        for op in ["=", "label", "<", "gotof", "+", "goto"]
    )
},

# ------------------------------------------------------------
# TRY / CATCH
# ------------------------------------------------------------
{
    "name": "try_catch_basic",
    "code": textwrap.dedent("""\
        try {
            print(1);
        } catch (e) {
            print(2);
        }
    """),
    "check": lambda q: (
        "catch_param" in ops_lower(q) and
        ops_lower(q).count("label") >= 2 and
        "goto" in ops_lower(q) and
        ops_lower(q).count("print") >= 2
    )
},

# ------------------------------------------------------------
# LISTAS / ARREGLOS
# ------------------------------------------------------------
{
    "name": "list_literal_get",
    "code": textwrap.dedent("""\
        let a: integer[] = [1, 2, 3];
        print(a[1]);
    """),
    "check": lambda q: (
        "newarr" in ops_lower(q) and
        ops_lower(q).count("setelem") >= 3 and
        "getelem" in ops_lower(q) and
        "print" in ops_lower(q)
    )
},

{
    "name": "list_index_set_and_get",
    "code": textwrap.dedent("""\
        let a: integer[] = [0, 0];
        a[1] = 7;
        print(a[1]);
    """),
    "check": lambda q: (
        "newarr" in ops_lower(q) and
        ops_lower(q).count("setelem") >= 3 and
        "getelem" in ops_lower(q) and
        "print" in ops_lower(q)
    )
},

{
    "name": "offset_basic",
    "code": textwrap.dedent("""\
        let arr: integer[] = [10, 20, 30, 40];
        let i: integer = 2;
        let val: integer = arr[i];
        print(val);
    """),
    "check": lambda q: (
        "newarr" in ops_lower(q) and
        ops_lower(q).count("setelem") >= 4 and
        "offset" in ops_lower(q) and
        "getelem" in ops_lower(q) and
        "print" in ops_lower(q)
    )
},

# ------------------------------------------------------------
# CLASES / OBJETOS
# ------------------------------------------------------------
{
    "name": "class_basic",
    "code": textwrap.dedent("""\
        class A {
            let x: integer = 1;
        }
    """),
    "check": lambda q: all(
        op in ops_lower(q) for op in ["class", "attr", "=", "endclass"]
    )
},

{
    "name": "class_basic_with_method",
    "code": textwrap.dedent("""\
        class Persona {
            let nombre: string = "Ana";
            function saludar() {
                print(this.nombre);
            }
        }
    """),
    "check": lambda q: (
        "class" in ops_lower(q) and
        "attr" in ops_lower(q) and
        "func" in ops_lower(q) and
        "print" in ops_lower(q) and
        "endfunc" in ops_lower(q) and
        "endclass" in ops_lower(q)
    )
},

{
    "name": "class_instantiation_and_method_call",
    "code": textwrap.dedent("""\
        class Greeter {
            function hello() {
                print(1);
            }
        }
        let g: Greeter = new Greeter();
        g.hello();
    """),
    "check": lambda q: (
        "class" in ops_lower(q) and
        "func" in ops_lower(q) and
        "endfunc" in ops_lower(q) and
        "endclass" in ops_lower(q) and
        "call" in ops_lower(q)
    )
},

]

def run_test(test: dict) -> dict:
    code = test["code"].strip()
    rc, out = run_driver(code)
    quads = parse_quads(out)

    try:
        ok = (rc == 0) and test["check"](quads)
    except Exception:
        ok = False
    return {
        "name": test["name"],
        "passed": ok,
        "code": code,
        "return_code": rc,
        "ops": ops(quads),
        "output": out if not ok else "\n".join(out.splitlines()[-10:])
    }

def main():
    if len(sys.argv) > 1:
        only = sys.argv[1]
        selected = [t for t in TESTS if t["name"].startswith(only)]
    else:
        selected = TESTS

    results = [run_test(t) for t in selected]
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    print(f"Tests Codegen (Driver): {passed}/{total} pasaron.")
    print()
    for r in results:
        mark = "✅" if r["passed"] else "❌"
        print(f"{mark} {r['name']}")
        print("********** Código **********")
        print(r['code'])
        print("*"*50)
        print("============ Salida Driver ============")
        print(r["output"])
        print("="*50)
        print("----------------- quadruples.txt -----------------")
        with open('quadruples.txt', 'r') as file:
            for line in file:
                print(line, end='')
        print("-"*50)
        print()

    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
