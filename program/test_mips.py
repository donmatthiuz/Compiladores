import sys, subprocess, pathlib, textwrap, re, tempfile

HERE = pathlib.Path(__file__).resolve().parent
DRIVER = HERE / "Driver.py"

HEADER_PATTERN = re.compile(r"^\s*Operador\s+Op1\s+Op2\s+Resultado\s*$")


# ------------------------------------------------------------
# LECTURA / PARSEO DE QUÁDUPLOS DESDE quadruples.txt
# ------------------------------------------------------------

def _parse_quads_from_text(text: str):
    """
    Parsea la tabla de cuádruplos desde un texto con encabezado:
    Operador   Op1   Op2   Resultado
    """
    lines = text.splitlines()
    quads = []
    started = False

    for line in lines:
        if not started:
            if HEADER_PATTERN.match(line):
                started = True
            continue

        stripped = line.strip()
        if not stripped:
            continue

        parts = [p.strip() for p in re.split(r"\s{2,}", stripped)]
        if 1 <= len(parts) <= 4:
            while len(parts) < 4:
                parts.append("")
            quads.append(tuple(parts))

    return quads


def parse_quads(stdout: str):
    """
    Leer los cuádruplos desde quadruples.txt.
    """
    quad_file = HERE / "quadruples.txt"
    if quad_file.exists():
        try:
            text = quad_file.read_text(encoding="utf-8")
            quads = _parse_quads_from_text(text)
            if quads:
                return quads
        except Exception as e:
            print(f"[WARN] No se pudo leer quadruples.txt: {e}", file=sys.stderr)

    # Fallback: intentar desde stdout
    quads = _parse_quads_from_text(stdout)
    return quads


def ops(quads):
    """Lista de operadores tal cual aparecen en la primera columna."""
    return [q[0] for q in quads]


def ops_lower(quads):
    """Operadores en minúsculas."""
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
            capture_output=True,
            text=True,
            cwd=HERE
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# ------------------------------------------------------------
# TESTS
# ------------------------------------------------------------

TESTS = [

    # --------------------------------------------------------
    # ARITMÉTICA
    # --------------------------------------------------------
    {
        "name": "arithmetic_basic_precedence",
        "code": textwrap.dedent("""\
            let a: integer = 5 + 2 * 3 - 1;
            print(a);
        """),
        "check": lambda q: subseq_in_order(
            ops_lower(q),
            ["*", "+", "-", "=", "print"]
        )
    },

    {
        "name": "arithmetic_with_division",
        "code": textwrap.dedent("""\
            let b: integer = 20 / 2 + 3;
            print(b);
        """),
        "check": lambda q: subseq_in_order(
            ops_lower(q),
            ["/", "+", "=", "print"]
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

    # --------------------------------------------------------
    # OPERACIONES LÓGICAS
    # --------------------------------------------------------
    {
        "name": "logical_operations",
        "code": textwrap.dedent("""\
            let x: boolean = true;
            let y: boolean = false;
            let z: boolean = x && !y || x;
            print(z);
        """),
        "check": lambda q: (
            "&&" in ops_lower(q) or "and" in ops_lower(q)
        ) and (
            "||" in ops_lower(q) or "or" in ops_lower(q)
        ) and (
            "not" in ops_lower(q) or "!" in ops_lower(q)
        ) and "print" in ops_lower(q)
    },

    # --------------------------------------------------------
    # RELACIONALES
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # CONTROL DE FLUJO: IF / ELSE
    # --------------------------------------------------------
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
        "check": lambda q: subseq_in_order(
            ops_lower(q),
            ["=", "==", "gotof", "print", "goto", "label", "print", "label"]
        )
    },

    # --------------------------------------------------------
    # CONTROL DE FLUJO: WHILE
    # --------------------------------------------------------
    {
        "name": "while_loop_increment",
        "code": textwrap.dedent("""\
            let i: integer = 0;
            while (i < 3) {
                i = i + 1;
                print(i);
            }
        """),
        "check": lambda q: subseq_in_order(
            ops_lower(q),
            ["=", "label", "<", "gotof", "+", "=", "print", "goto", "label"]
        )
    },

    # --------------------------------------------------------
    # CONTROL DE FLUJO: FOR
    # --------------------------------------------------------
    {
        "name": "for_loop_print",
        "code": textwrap.dedent("""\
            for (let j: integer = 0; j < 2; j = j + 1) {
                print(j);
            }
        """),
        "check": lambda q: subseq_in_order(
            ops_lower(q),
            ["=", "label", "<", "gotof", "print", "label", "+", "=", "goto", "label"]
        )
    },

    # --------------------------------------------------------
    # CONTROL DE FLUJO: DO/WHILE
    # --------------------------------------------------------
    {
        "name": "do_while_once_min",
        "code": textwrap.dedent("""\
            let y: integer = 0;
            do {
                y = y + 1;
            } while (y < 2);
        """),
        "check": lambda q: subseq_in_order(
            ops_lower(q),
            ["=", "label", "+", "=", "<", "gotof", "goto", "label"]
        )
    },

    # --------------------------------------------------------
    # SWITCH
    # --------------------------------------------------------
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
        "check": lambda q: (
            any(x[0] == "==" for x in q) and ops_lower(q).count("print") >= 2
        )
    },

    # --------------------------------------------------------
    # BREAK / CONTINUE EN WHILE
    # --------------------------------------------------------
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
        "check": lambda q: (
            "==" in ops_lower(q) and
            ops_lower(q).count("goto") >= 2 and
            ops_lower(q).count("label") >= 2 and
            "print" in ops_lower(q)
        )
    },

    # --------------------------------------------------------
    # TRY / CATCH
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # LISTAS / ARREGLOS
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # FUNCIONES
    # --------------------------------------------------------
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
        "check": lambda q: subseq_in_order(
            ops_lower(q),
            ["func", "param", "param", "+", "=", "return", "endfunc",
             "arg", "arg", "call", "=", "print"]
        )
    },

    {
        "name": "nested_function_calls",
        "code": textwrap.dedent("""\
            function add(a: integer, b: integer): integer { 
                return a + b; 
            }
            function square(x: integer): integer { 
                return x * x; 
            }
            let r: integer = square(add(2,3));
            print(r);
        """),
        "check": lambda q: (
            ops_lower(q).count("func") >= 2 and
            "return" in ops_lower(q) and
            ops_lower(q).count("endfunc") >= 2 and
            ops_lower(q).count("call") >= 2 and
            "print" in ops_lower(q)
        )
    },

    # --------------------------------------------------------
    # CLASES / OBJETOS
    # --------------------------------------------------------
    {
        "name": "class_basic",
        "code": textwrap.dedent("""\
            class A {
                let x: integer = 1;
            }
        """),
        "check": lambda q: subseq_in_order(
            ops_lower(q),
            ["class", "attr", "=", "endclass"]
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
        "name": "class_multiple_attrs_and_consts",
        "code": textwrap.dedent("""\
            class Punto {
                let x: integer = 0;
                let y: integer = 0;
                const DIM: integer = 2;
            }
        """),
        "check": lambda q: (
            "class" in ops_lower(q) and
            ops_lower(q).count("attr") >= 3 and
            ops_lower(q).count("=") >= 3 and
            "endclass" in ops_lower(q)
        )
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
        "check": lambda q: subseq_in_order(
            ops_lower(q),
            ["class", "func", "param", "param", "+", "return", "endfunc", "endclass"]
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
            "print" in ops_lower(q) and
            "endfunc" in ops_lower(q) and
            "endclass" in ops_lower(q) and
            ("new" in ops_lower(q) or "call" in ops_lower(q))
        )
    },

    {
        "name": "class_with_method_and_this_access",
        "code": textwrap.dedent("""\
            class C {
                let n: integer = 5;
                function inc() {
                    this.n = this.n + 1;
                }
            }
        """),
        "check": lambda q: (
            "class" in ops_lower(q) and
            "attr" in ops_lower(q) and
            "func" in ops_lower(q) and
            ("getattr" in ops_lower(q) or "+" in ops_lower(q)) and
            "endfunc" in ops_lower(q) and
            "endclass" in ops_lower(q)
        )
    },

    {
        "name": "class_with_multiple_methods",
        "code": textwrap.dedent("""\
            class Math {
                function sum(a: integer, b: integer): integer { return a + b; }
                function mul(a: integer, b: integer): integer { return a * b; }
            }
        """),
        "check": lambda q: (
            ops_lower(q).count("func") >= 2 and
            ops_lower(q).count("endfunc") >= 2 and
            "class" in ops_lower(q) and
            "endclass" in ops_lower(q)
        )
    },

    {
        "name": "function_return_class_instance",
        "code": textwrap.dedent("""\
            class P {}
            function make(): P { 
                return new P(); 
            }
            let p: P = make();
        """),
        "check": lambda q: (
            "class" in ops_lower(q) and
            "func" in ops_lower(q) and
            "return" in ops_lower(q) and
            ("new" in ops_lower(q) or "call" in ops_lower(q))
        )
    },

]


# ------------------------------------------------------------
# RUNNER DE TESTS
# ------------------------------------------------------------

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
        "output": out if not ok else "\n".join(out.splitlines()[-20:]),
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
    print(f"Tests Codegen MIPS: {passed}/{total} pasaron.\n")

    for r in results:
        mark = "✅" if r["passed"] else "❌"
        print(f"{mark} {r['name']}")
        print("********** Código **********")
        print(r['code'])
        print("*"*50)
        print("============ Salida Driver ============")
        print(r["output"])
        print("="*50)
        # print("----------------- quadruples.txt -----------------")
        # with open('quadruples.txt', 'r') as file:
        #     for line in file:
        #         print(line, end='')
        # print("-"*50)
        # print("----------------- mips_code.txt -----------------")
        # with open('mips_code.txt', 'r') as file:
        #     for line in file:
        #         print(line, end='')
        # print("-"*50)
        print()

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
