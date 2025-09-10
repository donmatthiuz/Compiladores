#!/usr/bin/env python3
"""
error_testing.py — Validador rápido de errores de Compiscript

Uso:
  python error_testing.py            # ejecuta todos los tests incluidos
  python error_testing.py TEST_NAME  # ejecuta solo un test por nombre (prefix match)

"""
import sys, subprocess, pathlib, textwrap

HERE = pathlib.Path(__file__).resolve().parent
DRIVER = HERE / "Driver.py"

# --------- Definición de tests ---------
# Cada test es un dict con:
#   name: nombre corto
#   code: fuente Compiscript
#   should_error: bool (True si esperamos error de tipado)
#   expect_contains: substring esperada en la salida cuando should_error=True
TESTS = [
    {
        "name": "non_boolean_if",
        "should_error": True,
        "expect_contains": "if",
        "code": textwrap.dedent("""\
    let x: integer = 1;
    if (x) { let y: integer = 0; }
"""),
    },
    {
        "name": "break_outside_loop",
        "should_error": True,
        "expect_contains": "break",
        "code": textwrap.dedent("""\
break;
"""),
    },
    {
        "name": "continue_outside_loop",
        "should_error": True,
        "expect_contains": "continue",
        "code": textwrap.dedent("""\
continue;
"""),
    },
    {
        "name": "return_outside_function",
        "should_error": True,
        "expect_contains": "return",
        "code": textwrap.dedent("""\
return 1;
"""),
    },
    {
        "name": "dot_nonexistent_attr",
        "should_error": True,
        "expect_contains": "no tiene atributo",
        "code": textwrap.dedent("""\
    class A { let b: integer; }
    let a: A = new A();
    let t = a.c;   // 'c' no existe
"""),
    },
    {
        "name": "dot_nonexistent_method",
        "should_error": True,
        "expect_contains": "no tiene miembro",
        "code": textwrap.dedent("""\
    class A {
      function f(): integer { return 1; }
    }
    let a: A = new A();
    a.g();   // 'g' no existe
"""),
    },
    {
        "name": "ctor_wrong_arg",
        "should_error": True,
        "expect_contains": "Constructor",
        "code": textwrap.dedent("""\
    class B { function constructor(x: integer) { } }
    let b: B = new B();  // falta el argumento
"""),
    },
    {
        "name": "ctor_wrong_type",
        "should_error": True,
        "expect_contains": "Constructor",
        "code": textwrap.dedent("""\
    class C { function constructor(x: string) { } }
    let c: C = new C(123);  // tipo incorrecto
"""),
    },
    {
        "name": "this_outside_method",
        "should_error": True,
        "expect_contains": "this",
        "code": textwrap.dedent("""\
this.nombre = "X";
"""),
    },
    {
        "name": "valid_class_usage",
        "should_error": False,
        "code": textwrap.dedent("""\
    class Animal {
      let nombre: string;
      function constructor(nombre: string) { this.nombre = nombre; }
      function hablar(): string { return this.nombre; }
    }
    let a: Animal = new Animal("Toby");
    let s: string = a.hablar();
"""),
    },
    {
        "name": "valid_control_flow",
        "should_error": False,
        "code": textwrap.dedent("""\
    let x: integer = 0;
    while (x < 2) { x = x + 1; }
    if (x == 2) { } else { }
    for (let i: integer = 0; i < 1; i = i + 1) { }
    do { x = x - 1; } while (x >= 0);
"""),
    },
    {
        "name": "non_boolean_while",
        "should_error": True,
        "expect_contains": "while",
        "code": textwrap.dedent("""\
    let x: integer = 0;
    while (1) { x = x + 1; }
"""),
    },
    {
        "name": "break_continue_inside_loop_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
    let s: integer = 0;
    while (s < 5) {
        s = s + 1;
        if (s == 1) { continue; }
        if (s == 3) { break; }
    }
"""),
    },
    {
        "name": "return_inside_function_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
function f(): integer { return 1; }
"""),
    },
    {
        "name": "prop_assign_type_mismatch",
        "should_error": True,
        "expect_contains": "atributo",
        "code": textwrap.dedent("""\
    class D { let n: integer; }
    let d: D = new D();
    d.n = "hola";  // tipo incompatible
"""),
    },
    {
        "name": "method_call_arg_type_mismatch",
        "should_error": True,
        "expect_contains": "Argumento",
        "code": textwrap.dedent("""\
    class E { function m(x: integer): integer { return x; } }
    let e: E = new E();
    let z = e.m("a");  // tipo de argumento incompatible
"""),
    },
    {
        "name": "list_elem_type_mismatch",
        "should_error": True,
        "expect_contains": "Elementos de la lista",
        "code": textwrap.dedent("""\
        let a = [1, "x"];
"""),
    },
    {
        "name": "list_ok_homog",
        "should_error": False,
        "code": textwrap.dedent("""\
        let a = [1, 2, 3];
"""),
    },
    {
        "name": "list_index_type_error",
        "should_error": True,
        "expect_contains": "Índice de lista",
        "code": textwrap.dedent("""\
        let a = [1,2,3];
        let x = a["0"];
"""),
    },
    {
        "name": "list_index_on_nonlist",
        "should_error": True,
        "expect_contains": "Indexación sobre no-lista",
        "code": textwrap.dedent("""\
        let x: integer = 10;
        let y = x[0];
"""),
    },
    {
        "name": "list_index_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
        let a = [1,2,3];
        let x = a[0];
"""),
    },
    {
        "name": "dead_code_after_return",
        "should_error": True,
        "expect_contains": "Código muerto",
        "code": textwrap.dedent("""\
        function f(): integer {
            return 1;
            print(2);
        }
"""),
    },
    {
        "name": "dead_code_after_break",
        "should_error": True,
        "expect_contains": "Código muerto",
        "code": textwrap.dedent("""\
        let i: integer = 0;
        while (true) {
            break;
            i = 1;
        }
"""),
    },
    {
        "name": "dead_code_after_continue",
        "should_error": True,
        "expect_contains": "Código muerto",
        "code": textwrap.dedent("""\
        let i: integer = 0;
        while (true) {
            continue;
            i = 1;
        }
"""),
    },
    {
        "name": "multiply_function_error",
        "should_error": True,
        "expect_contains": "no soportados",
        "code": textwrap.dedent("""\
        class C {
          function foo(a: integer): integer { return a; }
        }
        let c: C = new C();
        let x = c.foo * 2;
"""),
    },
    {
        "name": "duplicate_var_decl",
        "should_error": True,
        "expect_contains": "ya está declarada",
        "code": textwrap.dedent("""\
        let x: integer = 1;
        let x: integer = 2;
"""),
    },
    {
        "name": "duplicate_param_decl_fn",
        "should_error": True,
        "expect_contains": "Parámetro duplicado",
        "code": textwrap.dedent("""\
        function f(a: integer, a: integer): integer { return 1; }
"""),
    },
    {
        "name": "duplicate_param_decl_method",
        "should_error": True,
        "expect_contains": "Parámetro duplicado",
        "code": textwrap.dedent("""\
        class D {
            function m(a: integer, a: integer): integer { return 0; }
        }
"""),
    },
        {
        "name": "try_catch_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
    let lista: integer[] = [1,2,3];
    try {
      let x = lista[100];
    } catch (err) {
      let msg: string = "Error atrapado: " + err;
    }
"""),
    },
    {
        "name": "try_catch_scope_leak",
        "should_error": True,
        "expect_contains": "no definida",
        "code": textwrap.dedent("""\
    try { let a = 1; } catch (e) { let b = 2; }
    // 'e' no debe existir fuera del catch
    let z = e;
"""),
    },

]

def run_test(test, tmpdir: pathlib.Path) -> dict:
    src = test["code"].strip() + "\n"
    src_path = tmpdir / f"{test['name']}.cps"
    src_path.write_text(src, encoding="utf-8")

    try:
        proc = subprocess.run([sys.executable, str(DRIVER), str(src_path)],
                              capture_output=True, text=True, cwd=HERE)
    except FileNotFoundError:
        return {"name": test["name"], "passed": False, "should_error": test["should_error"],
                "output": "No se encontró Driver.py"}

    out = (proc.stdout or "") + (proc.stderr or "")
    out = out.strip()

    ok_expected_error = test['should_error']
    got_error = ("Type checking passed" not in out)

    passed = (ok_expected_error == got_error)

    if passed and ok_expected_error and test.get('expect_contains'):
        if test['expect_contains'].lower() not in out.lower():
            passed = False
            reason = f"Se esperaba que el mensaje contuviera '{test['expect_contains']}', salida:\n{out}"
        else:
            reason = out
    else:
        reason = out

    return {"name": test["name"], "passed": passed, "should_error": ok_expected_error, "output": reason}

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    tmpdir = HERE / '.tmp_tests'
    tmpdir.mkdir(exist_ok=True)

    selected = [t for t in TESTS if (not only or t['name'].startswith(only))]

    results = []
    for t in selected:
        results.append(run_test(t, tmpdir))

    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    print(f"\n=== Compiscript Error Testing ===")
    print(f"Tests ejecutados: {total} — Pasados: {passed} — Fallados: {total - passed}\n")

    for r in results:
        mark = "✅ PASA" if r.get("passed") else "❌ FALLA"
        print(f"{mark}  {r['name']}  (esperaba {'error' if r['should_error'] else 'ok'})")
        if not r.get('passed'):
            print("---- salida ----")
            print(r.get("output", ""))
            print("---------------")

    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
