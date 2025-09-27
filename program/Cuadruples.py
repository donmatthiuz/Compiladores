class QuadrupleTable:
    def __init__(self):
        # guardamos los cuádruplos como lista de tuplas
        self.quadruples = []

    def add(self, operator, op1, op2, result):
        self.quadruples.append((operator, op1, op2, result))

    def display(self):
        print(f"{'Operador':<10}{'Op1':<10}{'Op2':<10}{'Resultado':<10}")
        for q in self.quadruples:
            print(f"{q[0]:<10}{q[1]:<10}{str(q[2]):<10}{q[3]:<10}")


