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
    # =========================
    # Sistema de Tipos — Aritmética
    # =========================
    {
        "name": "arith_add_ok_int_float",
        "should_error": False,
        "code": textwrap.dedent("""\
    let a: integer = 1;
    let b: integer = 2;
    let c = a + b;
"""),
    },
    {
        "name": "arith_mul_type_error_str_int",
        "should_error": True,
        "expect_contains": "no soportados",
        "code": textwrap.dedent("""\
    let s: string = "x";
    let a = s * 2;
"""),
    },
    {
        "name": "arith_div_type_error_bool_float",
        "should_error": True,
        "expect_contains": "no soportados",
        "code": textwrap.dedent("""\
    let t: boolean = true;
    let a = t / 3;
"""),
    },
    {
        "name": "arith_mod_requires_integers",
        "should_error": True,
        "expect_contains": "solo soporta enteros",
        "code": textwrap.dedent("""\
    let x: integer = 5;
    let y: integer = 2;
    let f: string = "a";
    let z = x % 2;     // ok
    let w = f % x;     // error
"""),
    },

    # =========================
    # Sistema de Tipos — Lógicas
    # =========================
    {
        "name": "logic_and_type_error",
        "should_error": True,
        "expect_contains": "requiere booleanos",
        "code": textwrap.dedent("""\
    let a: integer = 1;
    let b: boolean = false;
    let c = a && b;
"""),
    },
    {
        "name": "logic_or_type_error",
        "should_error": True,
        "expect_contains": "requiere booleanos",
        "code": textwrap.dedent("""\
    let a: integer = 0;
    let c = a || true;
"""),
    },
    {
        "name": "logic_not_type_error",
        "should_error": True,
        "expect_contains": "no soportado",
        "code": textwrap.dedent("""\
    let a: integer = 1;
    let b = !a;
"""),
    },

    # =========================
    # Sistema de Tipos — Comparaciones
    # =========================
    {
        "name": "relational_requires_numeric",
        "should_error": True,
        "expect_contains": "requieren operandos numéricos",
        "code": textwrap.dedent("""\
    let s: string = "hi";
    let ok = 1 < 2;
    let bad = s >= 1;  // error
"""),
    },
    {
        "name": "equality_incompatible_types_should_error",
        "should_error": True,
        "expect_contains": "compat",
        "code": textwrap.dedent("""\
    let b: boolean = (1 == true);  // debería ser error por incompatibilidad
"""),
    },

    # =========================
    # Sistema de Tipos — Asignaciones
    # =========================
    {
        "name": "assign_type_mismatch",
        "should_error": True,
        "expect_contains": "No se puede asignar",
        "code": textwrap.dedent("""\
    let x: integer = 0;
    x = "hola";  // error
"""),
    },

    # =========================
    # Listas y estructuras
    # =========================
    {
        "name": "list_nested_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
    let m: integer[][] = [[1,2],[3,4]];
    let x: integer = m[0][1];
"""),
    },
    {
        "name": "list_nested_type_mismatch",
        "should_error": True,
        "expect_contains": "Elementos de la lista",
        "code": textwrap.dedent("""\
    let m = [[1,2], ["a"]];  // error, tipos heterogéneos en 2D
"""),
    },
    {
        "name": "list_class_subtyping_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
    class Animal { }
    class Perro : Animal { }
    let l = [ new Perro(), new Animal() ];
"""),
    },
    {
        "name": "list_index_type_error_2",
        "should_error": True,
        "expect_contains": "Índice de lista debe ser integer",
        "code": textwrap.dedent("""\
    let xs: integer[] = [1,2,3];
    let y = xs["0"];
"""),
    },

    # =========================
    # Manejo de Ámbito
    # =========================
    {
        "name": "undeclared_variable_use",
        "should_error": True,
        "expect_contains": "no definida",
        "code": textwrap.dedent("""\
    y = 10;   // sin declaración previa
"""),
    },
    {
        "name": "redeclaration_same_scope_var",
        "should_error": True,
        "expect_contains": "ya está declarada",
        "code": textwrap.dedent("""\
    let a: integer = 1;
    let a: integer = 2;  // redeclaración misma scope
"""),
    },
    {
        "name": "shadowing_in_inner_block_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
    let a: integer = 1;
    {
      let a: integer = 2;   // sombreado en bloque interno
      let b: integer = a;   // usa el interno
    }
    let c: integer = a;     // usa el externo
"""),
    },
    {
        "name": "use_out_of_block_scope_error",
        "should_error": True,
        "expect_contains": "no definida",
        "code": textwrap.dedent("""\
    {
      let a: integer = 2;
    }
    a = 3;  // fuera del bloque
"""),
    },
    {
        "name": "function_block_scope_isolated",
        "should_error": True,
        "expect_contains": "no definida",
        "code": textwrap.dedent("""\
    function f(): integer { let z: integer = 1; return z; }
    f();
    let q = z;   // z no existe aquí
"""),
    },

    # =========================
    # Funciones y Procedimientos
    # =========================
    {
        "name": "fn_call_wrong_arity",
        "should_error": True,
        "expect_contains": "Se esperaban",
        "code": textwrap.dedent("""\
    function f(x: integer, y: integer): integer { return x + y; }
    let r = f(1);  // falta un argumento
"""),
    },
    {
        "name": "fn_call_arg_type_mismatch",
        "should_error": True,
        "expect_contains": "Argumento incompatible",
        "code": textwrap.dedent("""\
    function inc(x: integer): integer { return x + 1; }
    let r = inc("a");  // tipo incorrecto
"""),
    },
    {
        "name": "fn_return_type_mismatch",
        "should_error": True,
        "expect_contains": "El tipo de retorno esperado",
        "code": textwrap.dedent("""\
    function s(): integer { return "hola"; }  // retorna string
"""),
    },
    {
        "name": "fn_recursion_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
    function fact(n: integer): integer {
    if (n <= 1) { return 1; }
    return n * fact(n - 1);
    }
    let f = fact(4);
    """),
    },
    {
        "name": "fn_nested_closure_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
    function outer(): integer {
      let a: integer = 1;
      function inner(): integer { return a; }
      return inner();
    }
    let x = outer();
"""),
    },
    {
        "name": "fn_nested_closure_bad_return",
        "should_error": True,
        "expect_contains": "tipo de retorno esperado",
        "code": textwrap.dedent("""\
    function outer(): integer {
      let a: string = "x";
      function inner(): integer { return a; }  // retorna string
      return inner();
    }
"""),
    },
    {
        "name": "duplicate_function_decl_same_scope",
        "should_error": True,
        "expect_contains": "ya definido",
        "code": textwrap.dedent("""\
    function h(): integer { return 1; }
    function h(): integer { return 2; }  // no hay sobrecarga
"""),
    },
    {
        "name": "call_undefined_function",
        "should_error": True,
        "expect_contains": "no definida",
        "code": textwrap.dedent("""\
    let r = foo();  // foo no existe
"""),
    },

    # =========================
    # Control de Flujo
    # =========================
    {
        "name": "if_cond_must_be_bool",
        "should_error": True,
        "expect_contains": "if",
        "code": textwrap.dedent("""\
    if (1) { }
"""),
    },
    {
        "name": "while_cond_must_be_bool",
        "should_error": True,
        "expect_contains": "while",
        "code": textwrap.dedent("""\
    while (0) { }
"""),
    },
    {
        "name": "do_while_cond_must_be_bool",
        "should_error": True,
        "expect_contains": "do-while",
        "code": textwrap.dedent("""\
    do { } while ("x");
"""),
    },
    # =========================
    # Clases y Objetos
    # =========================
    {
        "name": "class_duplicate_name",
        "should_error": True,
        "expect_contains": "Clase",
        "code": textwrap.dedent("""\
    class A { }
    class A { }  // duplicada
"""),
    },
    {
        "name": "class_duplicate_field",
        "should_error": True,
        "expect_contains": "Atributo",
        "code": textwrap.dedent("""\
    class C { let x: integer; let x: integer; }
"""),
    },
    {
        "name": "class_duplicate_method",
        "should_error": True,
        "expect_contains": "Método",
        "code": textwrap.dedent("""\
    class M { function m(): integer { return 1; } function m(): integer { return 2; } }
"""),
    },
    {
        "name": "method_call_wrong_arity",
        "should_error": True,
        "expect_contains": "Se esperaban",
        "code": textwrap.dedent("""\
    class A { function m(x: integer) { } }
    let a: A = new A();
    a.m();  // falta argumento
"""),
    },
    {
        "name": "this_outside_method_again",
        "should_error": True,
        "expect_contains": "this",
        "code": textwrap.dedent("""\
    this.x = 1;
"""),
    },

    # =========================
    # Generales
    # =========================
    {
        "name": "dead_code_after_return_in_fn",
        "should_error": True,
        "expect_contains": "Código muerto",
        "code": textwrap.dedent("""\
    function f(): integer {
      return 1;
      let z: integer = 2;  // muerto
    }
"""),
    },
    {
        "name": "multiply_function_error",
        "should_error": True,
        "expect_contains": "no soportados",
        "code": textwrap.dedent("""\
    function f(): integer { return 1; }
    let x = f * 2;   // no se puede multiplicar funciones
"""),
    },
    {
        "name": "duplicate_var_decl_again",
        "should_error": True,
        "expect_contains": "ya está declarada",
        "code": textwrap.dedent("""\
    let x: integer = 1;
    let x: integer = 2;
"""),
    },
    {
        "name": "duplicate_param_decl_method_again",
        "should_error": True,
        "expect_contains": "Parámetro duplicado",
        "code": textwrap.dedent("""\
    class A {
      function m(a: integer, a: integer) { }
    }
"""),
    },
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
    {
        "name": "inherit_override_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
    class Animal {
      function hablar(): string { return "ruido"; }
    }
    class Perro : Animal {
      function hablar(): string { return "guau"; }
    }
    let p: Perro = new Perro();
    let s: string = p.hablar();
"""),
    },
    {
        "name": "inherit_override_bad_params",
        "should_error": True,
        "expect_contains": "Firma incompatible",
        "code": textwrap.dedent("""\
    class A {
      function m(x: integer): integer { return x; }
    }
    class B : A {
      function m(): integer { return 1; }   # distinta aridad
    }
"""),
    },
    {
        "name": "inherit_override_bad_return",
        "should_error": True,
        "expect_contains": "retorno incompatible",
        "code": textwrap.dedent("""\
    class A {
      function m(): integer { return 1; }
    }
    class B : A {
      function m(): string { return "x"; }  # distinto tipo de retorno
    }
"""),
    },
    {
        "name": "inherit_field_access_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
    class A { let n: integer; }
    class B : A { }
    let b: B = new B();
    let z: integer = b.n;   // campo heredado
"""),
    },
    {
        "name": "inherit_ctor_from_base_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
    class A {
      function constructor(x: integer) { }
    }
    class B : A { }
    let b: B = new B(10);
"""),
    },
    {
        "name": "inherit_ctor_from_base_arity_error",
        "should_error": True,
        "expect_contains": "Constructor",
        "code": textwrap.dedent("""\
    class A {
      function constructor(x: integer, y: integer) { }
    }
    class B : A { }
    let b: B = new B(1);   // aridad incorrecta respecto al ctor heredado
"""),
    },
    {
        "name": "subtype_assignment_ok",
        "should_error": False,
        "code": textwrap.dedent("""\
    class Animal { }
    class Perro : Animal { }
    let a: Animal = new Perro();   // Perro <: Animal
"""),
    },
]

def run_test(test, tmpdir: pathlib.Path) -> dict:
    src = test["code"].strip() + "\n"
    src_path = tmpdir / f"{test['name']}.cps"
    src_path.write_text(src, encoding="utf-8")

    try:
        proc = subprocess.run(
            [sys.executable, str(DRIVER), str(src_path)],
            capture_output=True, text=True, cwd=HERE
        )
    except FileNotFoundError:
        return {"name": test["name"], "passed": False, "should_error": test["should_error"],
                "output": "No se encontró Driver.py"}

    out = (proc.stdout or "") + (proc.stderr or "")
    out = out.strip()

    ok_expected_error = test['should_error']
    got_error = (proc.returncode != 0)

    passed = (ok_expected_error == got_error)

    if passed and ok_expected_error and test.get('expect_contains'):
        if test['expect_contains'].lower() not in out.lower():
            passed = False
            reason = f"Se esperaba que el mensaje contuviera '{test['expect_contains']}', salida:\n{out}"
        else:
            reason = out
    else:
        reason = out

    return {
        "name": test["name"],
        "passed": passed,
        "should_error": ok_expected_error,
        "output": reason
    }

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    tmpdir = HERE / '.tmp_tests'
    tmpdir.mkdir(exist_ok=True)

    selected = [t for t in TESTS if (not only or t['name'].startswith(only))]

    results = [run_test(t, tmpdir) for t in selected]

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
