class QuadrupleTable:
    def __init__(self):
        self.quadruples = []
        self.temp_count = 0
        self.label_count = 0  # Para generar labels únicos

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def add(self, operator, op1, op2, result):
        self.quadruples.append((operator, op1, op2, result))
        return result

    def display(self):
        print(f"{'Operador':<10} {'Op1':<10} {'Op2':<10} {'Resultado':<10}")
        for quad in self.quadruples:
            op = quad[0] or ""
            op1 = quad[1] or ""
            op2 = quad[2] or ""
            res = quad[3] or ""
            print(f"{op:<10} {op1:<10} {op2:<10} {res:<10}")
