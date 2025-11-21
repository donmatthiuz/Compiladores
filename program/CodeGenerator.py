class CodeGenerator:
    """
    Generador de código MIPS a partir de una tabla de cuádruplos.
    NO requiere symbol_table - toda la información viene de los cuádruplos.
    """
    
    def __init__(self, quadruple_table):
        """
        Inicializa el generador de código MIPS.
        
        Args:
            quadruple_table: Tabla de cuádruplos a traducir
        """
        self.quads = quadruple_table.quadruples
        self.mips_code = []
        self.data_section = []
        self.text_section = []
        
        # Mapeo de temporales/variables a registros MIPS
        self.registers = {}
        self.available_regs = [f"$t{i}" for i in range(8)]  # $t0-$t7
        self.used_regs = set()
        
        # Mapeo de variables a posiciones en memoria (stack)
        self.var_offsets = {}
        self.current_offset = 0
    
    def _get_register(self, name):
        """
        Obtiene o asigna un registro para un temporal o variable.
        """
        if name in self.registers:
            return self.registers[name]
        
        # Buscar un registro disponible
        for reg in self.available_regs:
            if reg not in self.used_regs:
                self.registers[name] = reg
                self.used_regs.add(reg)
                return reg
        
        # Si no hay registros disponibles, reusar $t0 (simplificación)
        return "$t0"
    
    def _is_constant(self, operand):
        """
        Verifica si un operando es una constante numérica.
        """
        if operand is None or operand == "":
            return False
        return str(operand).lstrip('-').isdigit()
    
    def _is_temporary(self, operand):
        """
        Verifica si un operando es un temporal (t1, t2, etc.).
        """
        if operand is None or operand == "":
            return False
        return str(operand).startswith('t') and str(operand)[1:].isdigit()
    
    def _load_operand(self, operand):
        """
        Carga un operando en un registro.
        Puede ser: constante numérica, temporal, o variable.
        """
        if operand is None or operand == "":
            return None
        
        # CASO 1: Constante numérica
        if self._is_constant(operand):
            reg = self._get_register(f"const_{operand}")
            self.text_section.append(f"    li {reg}, {operand}  # Cargar constante {operand}")
            return reg
        
        # CASO 2: Temporal (t1, t2, etc.) - ya debe estar en registro
        if self._is_temporary(operand):
            return self._get_register(operand)
        
        # CASO 3: Variable - cargar desde memoria
        # Asignar offset si es la primera vez que vemos esta variable
        if operand not in self.var_offsets:
            self.var_offsets[operand] = self.current_offset
            self.current_offset += 4
        
        reg = self._get_register(f"var_{operand}")
        offset = self.var_offsets[operand]
        self.text_section.append(f"    lw {reg}, {offset}($sp)  # Cargar variable '{operand}'")
        return reg
    
    def _store_result(self, result, reg):
        """
        Almacena el resultado de una operación.
        """
        if result is None or result == "":
            return
        
        # Si es un temporal, ya está en el registro asignado
        if self._is_temporary(result):
            self.registers[result] = reg
            return
        
        # Si es una variable, guardarla en memoria
        if result not in self.var_offsets:
            self.var_offsets[result] = self.current_offset
            self.current_offset += 4
        
        offset = self.var_offsets[result]
        self.text_section.append(f"    sw {reg}, {offset}($sp)  # Guardar en '{result}'")
    
    def generate(self):
        """
        Genera el código MIPS completo a partir de los cuádruplos.
        """
        # Sección .data (para strings, constantes, etc.)
        self.data_section.append(".data")
        self.data_section.append("    newline: .asciiz \"\\n\"")
        self.data_section.append("")
        
        # Sección .text (código ejecutable)
        self.text_section.append(".text")
        self.text_section.append(".globl main")
        self.text_section.append("main:")
        
        # Reservar espacio en stack para variables (calculado dinámicamente)
        # Por ahora usamos 128 bytes, pero podríamos calcular el tamaño exacto
        stack_size = 128
        self.text_section.append(f"    addi $sp, $sp, -{stack_size}  # Reservar espacio en stack")
        self.text_section.append("")
        
        # Traducir cada cuádruplo
        for quad in self.quads:
            self._translate_quadruple(quad)
        
        self.text_section.append("")
        self.text_section.append(f"    addi $sp, $sp, {stack_size}  # Restaurar stack")
        self.text_section.append("    li $v0, 10  # Syscall exit")
        self.text_section.append("    syscall")
        
        # Combinar secciones
        self.mips_code = self.data_section + self.text_section
        return "\n".join(self.mips_code)
    
    def _translate_quadruple(self, quad):
        """
        Traduce un cuádruplo individual a código MIPS.
        """
        operator, op1, op2, result = quad
        op_str = str(operator) if operator is not None else ""
        op_lower = op_str.lower()
        
        # Asignación simple: result = op1
        if operator == "=":
            src_reg = self._load_operand(op1)
            if src_reg:
                dest_reg = self._get_register(result) if self._is_temporary(result) else src_reg
                if src_reg != dest_reg:
                    self.text_section.append(f"    move {dest_reg}, {src_reg}  # {result} = {op1}")
                self._store_result(result, dest_reg)
        
        # Operaciones aritméticas: +, -, *, /
        elif operator == "+":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    add {rd}, {r1}, {r2}  # {result} = {op1} + {op2}")
            self._store_result(result, rd)
        
        elif operator == "-":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    sub {rd}, {r1}, {r2}  # {result} = {op1} - {op2}")
            self._store_result(result, rd)
        
        elif operator == "*":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    mul {rd}, {r1}, {r2}  # {result} = {op1} * {op2}")
            self._store_result(result, rd)
        
        elif operator == "/":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    div {r1}, {r2}  # Dividir {op1} / {op2}")
            self.text_section.append(f"    mflo {rd}  # Obtener cociente en {result}")
            self._store_result(result, rd)
        
        # Operaciones relacionales: <, >, <=, >=, ==, !=
        elif operator == "<":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    slt {rd}, {r1}, {r2}  # {result} = ({op1} < {op2})")
            self._store_result(result, rd)
        
        elif operator == ">":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    slt {rd}, {r2}, {r1}  # {result} = ({op1} > {op2})")
            self._store_result(result, rd)
        
        elif operator == "<=":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    slt {rd}, {r2}, {r1}  # temp = ({op2} < {op1})")
            self.text_section.append(f"    xori {rd}, {rd}, 1  # {result} = !temp (para <=)")
            self._store_result(result, rd)
        
        elif operator == ">=":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    slt {rd}, {r1}, {r2}  # temp = ({op1} < {op2})")
            self.text_section.append(f"    xori {rd}, {rd}, 1  # {result} = !temp (para >=)")
            self._store_result(result, rd)
        
        elif operator == "==":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    xor {rd}, {r1}, {r2}  # XOR para comparar igualdad")
            self.text_section.append(f"    sltiu {rd}, {rd}, 1  # {result} = ({op1} == {op2})")
            self._store_result(result, rd)
        
        elif operator == "!=":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    xor {rd}, {r1}, {r2}  # XOR para comparar")
            self.text_section.append(f"    sltu {rd}, $zero, {rd}  # {result} = ({op1} != {op2})")
            self._store_result(result, rd)
        
        # Instrucciones de control de flujo
        elif op_lower == "label":
            # Formatos soportados:
            #   ("label", None, None, "L1")
            #   ("LABEL", "L1", None, None)
            label_name = result if result not in (None, "") else op1
            label = str(label_name).rstrip(":")
            self.text_section.append(f"{label}:")
        
        elif op_lower == "goto":
            # Formatos soportados:
            #   ("goto", "L1", None, None)
            #   ("GOTO", None, None, "L1")
            label = op1 or result
            self.text_section.append(f"    j {label}  # Salto incondicional")
        
        # Saltar si la condición es verdadera
        # Formatos:
        #   ("if",    cond, None, "L1")
        #   ("IF",    cond, None, "L1")
        #   ("ifTrue",cond, None, "L1")
        #   ("GOTOT", cond, None, "L1")
        elif op_lower in ("if", "iftrue", "gotot"):
            cond_reg = self._load_operand(op1)
            label = result if result not in (None, "") else op2
            self.text_section.append(
                f"    bne {cond_reg}, $zero, {label}  # if {op1} != 0 goto {label}"
            )
        
        # Saltar si la condición es falsa
        # Formatos:
        #   ("ifFalse", cond, None, "L1")
        #   ("IF_FALSE",cond, None, "L1")
        #   ("GOTOF",   cond, None, "L1")
        elif op_lower in ("iffalse", "if_false", "gotof"):
            cond_reg = self._load_operand(op1)
            label = result if result not in (None, "") else op2
            self.text_section.append(
                f"    beq {cond_reg}, $zero, {label}  # if {op1} == 0 goto {label}"
            )
        
        # Operación de impresión
        elif op_lower == "print":
            # El operando a imprimir puede estar en op1 o en result
            operand_to_print = result if result else op1
            reg = self._load_operand(operand_to_print)
            if reg:
                self.text_section.append(f"    move $a0, {reg}  # Preparar argumento para print")
                self.text_section.append(f"    li $v0, 1  # Syscall print integer")
                self.text_section.append(f"    syscall")
                # Imprimir newline
                self.text_section.append(f"    li $v0, 4  # Syscall print string")
                self.text_section.append(f"    la $a0, newline")
                self.text_section.append(f"    syscall")
        
        # Operador no reconocido
        else:
            self.text_section.append(f"    # Operador no manejado: {operator}")
    
    def save_to_file(self, filename="output.asm"):
        """
        Guarda el código MIPS generado en un archivo.
        """
        mips_code = self.generate()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(mips_code)
        print(f"✅ Código MIPS guardado en {filename}")
        return filename
    
    def get_mips_code(self):
        """
        Retorna el código MIPS como string.
        """
        return self.generate()


# Ejemplo de uso integrado
if __name__ == "__main__":
    from MarsExecutor import MarsExecutor
    
    # Simular una QuadrupleTable simple
    class QuadrupleTable:
        def __init__(self):
            self.quadruples = []
        
        def add(self, op, op1, op2, result):
            self.quadruples.append((op, op1, op2, result))
    
    # Crear tabla de cuádruplos de ejemplo
    # Código equivalente a: result = 5 + 3 * 2
    quad_table = QuadrupleTable()
    quad_table.add("=", "3", None, "t1")      # t1 = 3
    quad_table.add("=", "2", None, "t2")      # t2 = 2
    quad_table.add("*", "t1", "t2", "t3")     # t3 = t1 * t2  (3 * 2 = 6)
    quad_table.add("=", "5", None, "t4")      # t4 = 5
    quad_table.add("+", "t4", "t3", "t5")     # t5 = t4 + t3  (5 + 6 = 11)
    quad_table.add("PRINT", None, None, "t5") # print(t5)
    
    # Generar código MIPS
    print("🔧 Generando código MIPS...")
    codegen = CodeGenerator(quad_table)  # ¡SIN symbol_table!
    mips_code = codegen.get_mips_code()
    
    print("\n📝 Código MIPS generado:")
    print("=" * 60)
    print(mips_code)
    print("=" * 60)
    
    # Ejecutar con MARS
    print("\n🚀 Ejecutando en MARS...")
    try:
        executor = MarsExecutor()
        stdout, stderr, returncode = executor.execute_mips(mips_code)
        
        print("\n📤 Salida del programa:")
        print(stdout if stdout else "(sin salida)")
        
        if stderr:
            print("\n⚠️  Errores:")
            print(stderr)
        
        print(f"\n✅ Código de retorno: {returncode}")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("💡 Asegúrate de tener MARS instalado y configura la ruta correcta.")