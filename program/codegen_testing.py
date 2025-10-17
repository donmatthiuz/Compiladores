import sys, subprocess, pathlib, textwrap, re, tempfile

HERE = pathlib.Path(__file__).resolve().parent
DRIVER = HERE / "Driver.py"

HEADER_PATTERN = re.compile(r"^\s*Operador\s+Op1\s+Op2\s+Resultado\s*$")

def parse_quads(stdout: str):
    """
    Extrae cuádruplos de la salida del runner
    """
    lines = stdout.splitlines()
    quads = []
    started = False
    for line in lines:
        if not started:
            if HEADER_PATTERN.match(line):
                started = True
            continue
        parts = [p.strip() for p in re.split(r"\s{2,}", line.strip())]
        if 1 <= len(parts) <= 4:
            while len(parts) < 4:
                parts.append("")
            quads.append(tuple(parts))
    return quads

def ops(quads):
    return [q[0] for q in quads]

def find_indices(quads, op):
    return [i for i, q in enumerate(quads) if q[0] == op]

def subseq_in_order(sequence, pattern):
    it = iter(sequence)
    return all(any(x == y for x in it) for y in pattern)

def run_driver(code: str):
    """
    Escribe a un archivo temporal .cps, ejecuta Driver.py en modo 'runner'
    y devuelve return_code con la salida_combinada
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
# EXPRESIONES Y OPERACIONES BÁSICAS
# ------------------------------------------------------------
{
    "name": "arithmetic_operations",
    "code": textwrap.dedent("""\
        let a: integer = 5 + 2 * 3 - 1;
        print(a);
    """),
    "check": lambda q: subseq_in_order(ops(q), ["*", "+", "-", "=", "print"])
},
{
    "name": "logical_operations",
    "code": textwrap.dedent("""\
        let x: boolean = true;
        let y: boolean = false;
        let z: boolean = x && !y || x;
        print(z);
    """),
    "check": lambda q: subseq_in_order(ops(q), ["=", "=", "not", "&&", "||", "=", "print"])
},


# ------------------------------------------------------------
# CONTROL DE FLUJO
# ------------------------------------------------------------
{
    "name": "if_else_basic",
    "code": textwrap.dedent("""\
        let x: integer = 0;
        if (x == 0) { print(1); } else { print(2); }
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["=", "==", "gotof", "print", "goto", "label", "print", "label"])
},
{
    "name": "while_loop_increment",
    "code": textwrap.dedent("""\
        let i: integer = 0;
        while (i < 3) { i = i + 1; }
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["=", "label", "<", "gotof", "+", "=", "goto", "label"])
},
{
    "name": "for_loop_print",
    "code": textwrap.dedent("""\
        for (let j: integer = 0; j < 2; j = j + 1) { print(j); }
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["=", "label", "<", "gotof", "print", "label", "+", "=", "goto", "label"])
},
{
    "name": "do_while_once_min",
    "code": textwrap.dedent("""\
        let y: integer = 0;
        do { y = y + 1; } while (y < 2);
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["=", "label", "+", "=", "<", "gotof", "goto", "label"])
},
{
    "name": "switch_no_fallthrough",
    "code": textwrap.dedent("""\
        let k: integer = 2;
        switch (k) {
          case 1: print(10);
          case 2: print(20);
          default: print(99);
        }
    """),
    "check": lambda q: any(x[0] == "==" for x in q) and any(x[0] == "print" for x in q)
},
{
    "name": "break_continue_in_while",
    "code": textwrap.dedent("""\
        let i: integer = 0;
        while (i < 5) {
            i = i + 1;
            if (i == 2) { continue; }
            if (i == 4) { break; }
            print(i);
        }
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["=", "label", "<", "gotof", "+", "=", "==", "gotof", "goto",
         "==", "gotof", "goto", "print", "goto", "label"])
},


# ------------------------------------------------------------
# ARREGLOS
# ------------------------------------------------------------
{
    "name": "list_literal_get",
    "code": textwrap.dedent("""\
        let a: integer[] = [1, 2, 3];
        print(a[1]);
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["newarr", "setelem", "setelem", "setelem", "=", "getelem", "print"])
},
{
    "name": "list_index_set_and_get",
    "code": textwrap.dedent("""\
        let a: integer[] = [0, 0];
        a[1] = 7;
        print(a[1]);
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["newarr", "setelem", "setelem", "=", "getelem", "getelem", "print"])
},
{
    "name": "nested_list_2d",
    "code": textwrap.dedent("""\
        let m: integer[][] = [[1,2],[3,4]];
        print(m[1][0]);
        m[0][1] = 9;
        print(m[0][1]);
    """),
    "check": lambda q: (
        ops(q).count("newarr") >= 2 and
        ops(q).count("setelem") >= 4 and
        subseq_in_order(ops(q), ["=", "getelem", "getelem", "print", "getelem", "getelem", "print"])
    )
},


# ------------------------------------------------------------
# FUNCIONES
# ------------------------------------------------------------
{
    "name": "function_with_return",
    "code": textwrap.dedent("""\
        function sum(a: integer, b: integer): integer {
            let c: integer = a + b;
            return c;
        }
        let r: integer = sum(3, 4);
        print(r);
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["func", "param", "param", "+", "=", "return", "endfunc",
         "arg", "arg", "call", "=", "print"])
},
{
    "name": "nested_function_calls",
    "code": textwrap.dedent("""\
        function add(a: integer, b: integer): integer { return a + b; }
        function square(x: integer): integer { return x * x; }
        let r: integer = square(add(2,3));
        print(r);
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["func", "param", "param", "+", "return", "endfunc",
         "func", "param", "*", "return", "endfunc",
         "arg", "arg", "call", "arg", "call", "=", "print"])
},


# ------------------------------------------------------------
# TRY / CATCH
# ------------------------------------------------------------
{
    "name": "try_catch_block",
    "code": textwrap.dedent("""\
        try {
            print(1);
        } catch (e) {
            print(2);
        }
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["label", "print", "goto", "label", "catch_param", "print", "label"])
},


# ------------------------------------------------------------
# OFFSET
# ------------------------------------------------------------
{
    "name": "offset_basic",
    "code": textwrap.dedent("""\
        let arr: integer[] = [10, 20, 30, 40];
        let i: integer = 2;
        let val: integer = arr[i];
        print(val);
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["newarr", "setelem", "setelem", "setelem", "setelem", "=", "offset", "getelem", "=", "print"])
},


# ------------------------------------------------------------
# CLASES
# ------------------------------------------------------------
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
    "check": lambda q: subseq_in_order(ops(q),
        ["class", "attr", "=", "func", "param", "print", "endfunc", "endclass"])
},
{
    "name": "class_multiple_attrs_and_consts",
    "code": textwrap.dedent("""\
        class Punto {
            let x: integer = 0;
            let y: integer = 0;
            const DIM: integer = 2;
        }
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["class", "attr", "=", "attr", "=", "attr", "=", "endclass"])
},
{
    "name": "class_with_method_return",
    "code": textwrap.dedent("""\
        class Calculadora {
            function sumar(a: integer, b: integer): integer {
                return a + b;
            }
        }
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["class", "func", "param", "param", "+", "return", "endfunc", "endclass"])
},
{
    "name": "class_attribute_access_with_this",
    "code": textwrap.dedent("""\
        class C {
            let n: integer = 5;
            function inc() {
                this.n = this.n + 1;
            }
        }
    """),
    "check": lambda q: subseq_in_order(ops(q),
        ["class", "attr", "=", "func", "param", "getattr", "getattr", "+", "setelem", "endfunc", "endclass"])
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
    "check": lambda q: subseq_in_order(ops(q),
        ["class", "func", "param", "print", "endfunc", "endclass",
         "=", "call"])
},
{
    "name": "class_basic",
    "code": """
        class A {
            let x: integer = 1;
        }
    """,
    "check": lambda q: subseq_in_order(ops(q), ["class","attr","=","endclass"])
},
{
    "name": "class_with_method_and_this_access",
    "code": """
        class C {
            let n: integer = 5;
            function inc() {
                this.n = this.n + 1;
            }
        }
    """,
    "check": lambda q: "getattr" in ops(q) and ("+" in ops(q) or "setelem" in ops(q))
},
{
    "name": "class_with_multiple_methods",
    "code": """
        class Math {
            function sum(a: integer, b: integer): integer { return a + b; }
            function mul(a: integer, b: integer): integer { return a * b; }
        }
    """,
    "check": lambda q: ops(q).count("func") == 2 and ops(q).count("endfunc") == 2
},
{
    "name": "function_return_class_instance",
    "code": """
        class P {}
        function make(): P { return new P(); }
        let p: P = make();
    """,
    "check": lambda q: "class" in ops(q) and "call" in ops(q)
},
{
    "name": "nested_classes",
    "code": """
        class Outer {
            let a: integer = 1;
            class Inner {
                let b: integer = 2;
            }
        }
    """,
    "check": lambda q: ops(q).count("class") >= 2 and "endclass" in ops(q)
},
]

def run_test(test: dict) -> dict:
    code = test["code"].strip()
    rc, out = run_driver(code)
    quads = parse_quads(out)
    ok = (rc == 0) and test["check"](quads)
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
    print(f"Tests Codegen: {passed}/{total} pasaron.")
    for r in results:
        mark = "✅" if r["passed"] else "❌"
        print(f"{mark} {r['name']}")
        # print("********** Código **********")
        # print(r['code'])
        # print("****************************")
        # print("============ Tabla reconstruida ============")
        # print(r["output"][:8000])
        # print("============================================")
        if not r["passed"]:
            print("********** Código **********")
            print(r['code'])
            print("****************************")
            print("============ Tabla reconstruida ============")
            print(r["output"][:8000])
            print("============================================")
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
