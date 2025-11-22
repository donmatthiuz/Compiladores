function SumaRecursiva(n: integer): integer {
    if (n <= 0) {
        return 0;
    } else {
        return n + SumaRecursiva(n - 1);
    }
}

var res = SumaRecursiva(8);
print(res);  // Esto imprimirá 36 (1+2+3+...+8)