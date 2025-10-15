import sys, subprocess, pathlib, textwrap, re, tempfile

HERE = pathlib.Path(__file__).resolve().parent
DRIVER = HERE / "Driver.py"

HEADER_PATTERN = re.compile(r"^\s*Operador\s+Op1\s+Op2\s+Resultado\s*$")

def parse_quads(stdout: str):
    lines = stdout.splitlines()
    quads = []
    started = False
    for line in lines:
        if not started:
            if HEADER_PATTERN.match(line):
                started = True
            continue
        parts = [p.strip() for p in re.split(r"\s{2,}", line.strip())]
        if len(parts) == 4:
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
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        src = td / "tmp.cps"
        src.write_text(code, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(DRIVER), str(src), "runner"],
            capture_output=True, text=True, cwd=HERE
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

TESTS = [
    {
        "name": "if_else_basic",
        "code": textwrap.dedent("""\
            let x: integer = 0;
            if (x == 0) { print(1); } else { print(2); }
        """),
        "check": lambda quads: (
            subseq_in_order(ops(quads), ["=", "==", "gotof", "print", "goto", "label", "print", "label"]) and
            (lambda i_gotof, i_goto, quads: (
                i_gotof < i_goto and
                any(idx > i_goto and quads[idx][0] == "label" and quads[idx][3] == quads[i_gotof][3]
                    for idx in range(i_gotof+1, len(quads))) and
                any(idx > i_goto and quads[idx][0] == "label" and quads[idx][3] == quads[i_goto][3]
                    for idx in range(i_goto+1, len(quads)))
            ))(find_indices(quads, "gotof")[0], find_indices(quads, "goto")[0], quads)
        )
    },
    {
        "name": "while_loop_increment",
        "code": textwrap.dedent("""\
            let i: integer = 0;
            while (i < 3) { i = i + 1; }
        """),
        "check": lambda quads: (
            subseq_in_order(ops(quads), ["=", "label", "<", "gotof", "+", "=", "goto", "label"]) and
            (lambda i_start_label, i_gotof, i_goto, quads: (
                i_start_label < i_gotof < i_goto and
                quads[i_goto][3] == quads[i_start_label][3]
            ))(find_indices(quads, "label")[0], find_indices(quads, "gotof")[0], find_indices(quads, "goto")[-1], quads)
        )
    },
    {
        "name": "for_loop_print",
        "code": textwrap.dedent("""\
            for (let j: integer = 0; j < 2; j = j + 1) { print(j); }
        """),
        "check": lambda quads: (
            subseq_in_order(ops(quads), ["=", "label", "<", "gotof", "print", "label", "+", "=", "goto", "label"])
        )
    },
    {
        "name": "do_while_once_min",
        "code": textwrap.dedent("""\
            let y: integer = 0;
            do { y = y + 1; } while (y < 2);
        """),
        "check": lambda quads: (
            subseq_in_order(ops(quads), ["=", "label", "+", "=", "<", "gotof", "goto", "label"])
        )
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
        "check": lambda quads: (
            any(q[0] == "==" for q in quads) and
            [q for q in quads if q[0] == "print"] and
            quads[-1][0] == "label"
        )
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
        "check": lambda quads: (
            subseq_in_order(ops(quads),
                            ["=", "label", "<", "gotof", "+", "=", "==", "gotof", "goto",
                             "==", "gotof", "goto", "print", "goto", "label"])
        )
    },
]

def run_test(test: dict) -> dict:
    code = test["code"].strip() + "\\n"
    rc, out = run_driver(code)
    quads = parse_quads(out)
    ok = (rc == 0) and test["check"](quads)
    return {
        "name": test["name"],
        "passed": ok,
        "return_code": rc,
        "ops": ops(quads),
        "output": out if not ok else "\\n".join(out.splitlines()[-10:])
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
    print(f"Tests Codegen: {passed}/{total} pasaron.\\n")
    for r in results:
        mark = "✅" if r["passed"] else "❌"
        print(f"{mark} {r['name']}")
        if not r["passed"]:
            print("---- salida del runner ----")
            print(r["output"][:8000])
            print("---------------------------")
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
