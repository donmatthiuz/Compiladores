class CodeGenerator:
    """
    Generador de código MIPS a partir de una tabla de cuádruplos.
    Con soporte completo para funciones recursivas, etiquetas únicas y ARRAYS.
    """
    
    def __init__(self, quadruple_table):
        self.quads = quadruple_table.quadruples
        self.mips_code = []
        self.data_section = []
        self.text_section = []
        
        # Mapeo de temporales/variables
        self.registers = {}
        self.available_regs = [f"$t{i}" for i in range(10)]
        
        # Información de funciones
        self.functions = {}
        self.current_function = "main"
        self.label_counter = 0
        self.function_labels = {}
        
        # Información de arrays
        self.arrays = {}  # {nombre: {'size': int, 'address': str}}
        self.heap_pointer = 0x10010000  # Dirección inicial del heap
        
    def _get_register(self, name):
        """Obtiene o asigna un registro."""
        if name in self.registers:
            return self.registers[name]
        
        for reg in self.available_regs:
            if reg not in self.registers.values():
                self.registers[name] = reg
                return reg
        
        return "$t0"
    
    def _new_label(self, base_name=""):
        """Genera una nueva etiqueta única con prefijo de función."""
        self.label_counter += 1
        if base_name:
            return f"{self.current_function}_{base_name}_{self.label_counter}"
        return f"{self.current_function}_L{self.label_counter}"
    
    def _is_constant(self, operand):
        if operand is None or operand == "":
            return False
        return str(operand).lstrip('-').isdigit()
    
    def _is_temporary(self, operand):
        if operand is None or operand == "":
            return False
        return str(operand).startswith('t') and str(operand)[1:].isdigit()
    
    def _load_operand(self, operand):
        """Carga un operando en un registro."""
        if operand is None or operand == "":
            return None
        
        if self._is_constant(operand):
            reg = self._get_register(f"const_{operand}")
            self.text_section.append(f"    li {reg}, {operand}")
            return reg
        
        if self._is_temporary(operand):
            return self._get_register(operand)
        
        # Para parámetros en funciones
        if self.current_function != "main" and operand in self.functions.get(self.current_function, {}).get('params', []):
            param_index = self.functions[self.current_function]['params'].index(operand)
            reg = self._get_register(operand)
            self.text_section.append(f"    lw {reg}, {16 + param_index * 4}($fp)  # Cargar parámetro {operand}")
            return reg
        
        return self._get_register(operand)
    
    def generate(self):
        """Genera el código MIPS completo."""
        # Sección .data
        self.data_section.append(".data")
        self.data_section.append("newline: .asciiz \"\\n\"")
        self.data_section.append("")
        
        # Sección .text
        self.text_section.append(".text")
        self.text_section.append(".globl main")
        self.text_section.append("")
        
        # Identificar funciones
        self._identify_functions()
        
        # Generar main primero
        self._generate_main()
        
        # Generar funciones después
        self._generate_functions()
        
        # Combinar secciones
        self.mips_code = self.data_section + self.text_section
        return "\n".join(self.mips_code)
    
    def _identify_functions(self):
        """Identifica todas las funciones en los cuádruplos."""
        current_func = None
        
        for i, quad in enumerate(self.quads):
            operator, op1, op2, result = quad
            op_str = str(operator).lower() if operator else ""
            
            if op_str == "func":
                current_func = result if result else op1
                self.functions[current_func] = {
                    'start': i,
                    'end': None,
                    'params': [],
                    'labels': set()
                }
            elif op_str == "endfunc" and current_func:
                self.functions[current_func]['end'] = i
                current_func = None
            elif op_str == "param" and current_func:
                param_name = op1 if op1 else result
                if param_name and param_name not in self.functions[current_func]['params']:
                    self.functions[current_func]['params'].append(param_name)
            elif op_str == "label" and current_func:
                label_name = result if result else op1
                if label_name:
                    self.functions[current_func]['labels'].add(label_name)
    
    def _generate_main(self):
        """Genera el código para la función main."""
        self.text_section.append("main:")
        
        # Encontrar los cuádruplos que pertenecen a main
        main_quads = []
        in_function = False
        
        for quad in self.quads:
            operator, op1, op2, result = quad
            op_str = str(operator).lower() if operator else ""
            
            if op_str == "func":
                in_function = True
            elif op_str == "endfunc":
                in_function = False
                continue
            
            if not in_function and op_str not in ["func", "endfunc"]:
                main_quads.append(quad)
        
        # Generar código para main
        for quad in main_quads:
            self._translate_quadruple(quad)
        
        # Salir al final de main
        self.text_section.append("    li $v0, 10")
        self.text_section.append("    syscall")
        self.text_section.append("")
    
    def _generate_functions(self):
        """Genera código para todas las funciones."""
        for func_name, func_info in self.functions.items():
            if func_name == "main":
                continue
                
            self.current_function = func_name
            self.label_counter = 0
            
            self.text_section.append(f"{func_name}:")
            
            # Stack frame para función recursiva
            self.text_section.append("    addi $sp, $sp, -16")
            self.text_section.append("    sw $ra, 12($sp)")
            self.text_section.append("    sw $fp, 8($sp)")
            self.text_section.append("    move $fp, $sp")
            
            # Guardar parámetros
            for i, param in enumerate(func_info['params']):
                if i < 4:
                    self.text_section.append(f"    sw $a{i}, {16 + i*4}($fp)  # Guardar parámetro {param}")
            
            # Generar código del cuerpo de la función
            start = func_info['start'] + 1
            end = func_info['end']
            
            for i in range(start, end):
                quad = self.quads[i]
                self._translate_quadruple(quad)
            
            # Cleanup del stack frame
            self.text_section.append(f"{func_name}_end:")
            self.text_section.append("    lw $ra, 12($sp)")
            self.text_section.append("    lw $fp, 8($sp)")
            self.text_section.append("    addi $sp, $sp, 16")
            self.text_section.append("    jr $ra")
            self.text_section.append("")
            
            self.current_function = "main"
    
    def _translate_quadruple(self, quad):
        """Traduce un cuádruplo individual a código MIPS."""
        operator, op1, op2, result = quad
        op_str = str(operator).lower() if operator else ""
        
        # ==================== OPERACIONES DE ARRAYS ====================
        
        # NEWARR: Crear un nuevo array en memoria
        if op_str == "newarr":
            size = int(op1) if op1 else 0
            array_temp = result
            
            # Calcular bytes necesarios (size * 4)
            bytes_needed = size * 4
            
            # Guardar dirección del array en registro
            array_reg = self._get_register(array_temp)
            self.text_section.append(f"    # newarr: Crear array de tamaño {size}")
            self.text_section.append(f"    li {array_reg}, {self.heap_pointer}  # Dirección base del array")
            
            # Guardar información del array
            self.arrays[array_temp] = {
                'size': size,
                'address': self.heap_pointer
            }
            
            # Avanzar heap pointer
            self.heap_pointer += bytes_needed
        
        # SETELEM: Asignar valor a un elemento del array
        elif op_str == "setelem":
            array_name = op1
            index = op2
            value = result
            
            # Obtener registro del array
            array_reg = self._get_register(array_name)
            
            # Cargar el valor a asignar
            value_reg = self._load_operand(value)
            
            # Si el índice es constante
            if self._is_constant(index):
                offset = int(index) * 4
                self.text_section.append(f"    # setelem: {array_name}[{index}] = {value}")
                self.text_section.append(f"    sw {value_reg}, {offset}({array_reg})")
            else:
                # Si el índice es variable
                index_reg = self._load_operand(index)
                temp_reg = "$t9"  # Usar un registro temporal
                self.text_section.append(f"    # setelem: {array_name}[{index}] = {value}")
                self.text_section.append(f"    sll {temp_reg}, {index_reg}, 2  # Multiplicar índice por 4")
                self.text_section.append(f"    add {temp_reg}, {array_reg}, {temp_reg}  # Calcular dirección")
                self.text_section.append(f"    sw {value_reg}, 0({temp_reg})  # Guardar valor")
        
        # OFFSET: Calcular dirección de un elemento (usado antes de getelem)
        elif op_str == "offset":
            array_name = op1
            index = op2
            result_temp = result
            
            # Obtener registro del array
            array_reg = self._get_register(array_name)
            
            # Cargar el índice
            index_reg = self._load_operand(index)
            
            # Calcular offset
            result_reg = self._get_register(result_temp)
            self.text_section.append(f"    # offset: Calcular {array_name}[{index}]")
            self.text_section.append(f"    sll {result_reg}, {index_reg}, 2  # Multiplicar índice por 4")
            self.text_section.append(f"    add {result_reg}, {array_reg}, {result_reg}  # Sumar base + offset")
        
        # GETELEM: Obtener valor de un elemento del array
        elif op_str == "getelem":
            array_name = op1
            offset_or_index = op2
            result_temp = result
            
            array_reg = self._get_register(array_name)
            result_reg = self._get_register(result_temp)
            
            # Si op2 es el resultado de un offset, ya es una dirección
            if offset_or_index and str(offset_or_index).startswith('t'):
                offset_reg = self._get_register(offset_or_index)
                self.text_section.append(f"    # getelem: Cargar elemento del array")
                self.text_section.append(f"    lw {result_reg}, 0({offset_reg})")
            else:
                # Si es un índice directo
                if self._is_constant(offset_or_index):
                    offset = int(offset_or_index) * 4
                    self.text_section.append(f"    # getelem: {array_name}[{offset_or_index}]")
                    self.text_section.append(f"    lw {result_reg}, {offset}({array_reg})")
                else:
                    index_reg = self._load_operand(offset_or_index)
                    temp_reg = "$t9"
                    self.text_section.append(f"    # getelem: {array_name}[{offset_or_index}]")
                    self.text_section.append(f"    sll {temp_reg}, {index_reg}, 2")
                    self.text_section.append(f"    add {temp_reg}, {array_reg}, {temp_reg}")
                    self.text_section.append(f"    lw {result_reg}, 0({temp_reg})")
        
        # ==================== RESTO DE OPERACIONES ====================
        
        # ASIGNACIÓN
        elif operator == "=":
            src_reg = self._load_operand(op1)
            if src_reg and result:
                dest_reg = self._get_register(result)
                if src_reg != dest_reg:
                    self.text_section.append(f"    move {dest_reg}, {src_reg}  # {result} = {op1}")
        
        # ARITMÉTICA
        elif operator == "+":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    add {rd}, {r1}, {r2}  # {result} = {op1} + {op2}")
        
        elif operator == "-":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    sub {rd}, {r1}, {r2}  # {result} = {op1} - {op2}")
        
        elif operator == "*":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    mul {rd}, {r1}, {r2}  # {result} = {op1} * {op2}")
        
        elif operator == "/":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    div {r1}, {r2}  # Dividir {op1} / {op2}")
            self.text_section.append(f"    mflo {rd}  # Obtener cociente en {result}")
        
        # COMPARACIONES
        elif operator == "<":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    slt {rd}, {r1}, {r2}  # {result} = ({op1} < {op2})")
        
        elif operator == ">":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    slt {rd}, {r2}, {r1}  # {result} = ({op1} > {op2})")
        
        elif operator == "<=":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    slt {rd}, {r2}, {r1}  # temp = ({op2} < {op1})")
            self.text_section.append(f"    xori {rd}, {rd}, 1  # {result} = !temp (para <=)")
        
        elif operator == ">=":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    slt {rd}, {r1}, {r2}  # temp = ({op1} < {op2})")
            self.text_section.append(f"    xori {rd}, {rd}, 1  # {result} = !temp (para >=)")
        
        elif operator == "==":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    xor {rd}, {r1}, {r2}  # XOR para comparar igualdad")
            self.text_section.append(f"    sltiu {rd}, {rd}, 1  # {result} = ({op1} == {op2})")
        
        elif operator == "!=":
            r1 = self._load_operand(op1)
            r2 = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    xor {rd}, {r1}, {r2}  # XOR para comparar")
            self.text_section.append(f"    sltu {rd}, $zero, {rd}  # {result} = ({op1} != {op2})")
        
        # LLAMADA A FUNCIÓN
        elif op_str == "call":
            func_name = op1 if op1 else result
            used_regs = [reg for reg in self.registers.values() if reg.startswith('$t')]
            stack_space = len(used_regs) * 4
            if stack_space > 0:
                self.text_section.append(f"    addi $sp, $sp, -{stack_space}")
                for i, reg in enumerate(used_regs):
                    self.text_section.append(f"    sw {reg}, {i*4}($sp)")
            
            self.text_section.append(f"    jal {func_name}  # Llamar a {func_name}")
            
            if stack_space > 0:
                for i, reg in enumerate(used_regs):
                    self.text_section.append(f"    lw {reg}, {i*4}($sp)")
                self.text_section.append(f"    addi $sp, $sp, {stack_space}")
            
            if result:
                self.text_section.append(f"    move {self._get_register(result)}, $v0  # {result} = resultado")
        
        # ARGUMENTOS
        elif op_str == "arg":
            arg_value = op1 if op1 else result
            arg_index = int(op2) if op2 else 0
            reg = self._load_operand(arg_value)
            if arg_index < 4:
                self.text_section.append(f"    move $a{arg_index}, {reg}  # Pasar argumento {arg_index}: {arg_value}")
        
        # RETORNO
        elif op_str == "return":
            return_value = op1 if op1 else result
            if return_value:
                reg = self._load_operand(return_value)
                self.text_section.append(f"    move $v0, {reg}  # Retornar {return_value}")
            self.text_section.append(f"    j {self.current_function}_end")
        
        # ETIQUETAS
        elif op_str == "label":
            label_name = result if result else op1
            unique_label = f"{self.current_function}_{label_name}"
            self.text_section.append(f"{unique_label}:")
        
        # SALTOS
        elif op_str == "goto":
            label = op1 or result
            unique_label = f"{self.current_function}_{label}"
            self.text_section.append(f"    j {unique_label}")
        
        # SALTOS CONDICIONALES
        elif op_str in ["if", "iftrue", "gotot"]:
            cond_reg = self._load_operand(op1)
            label = result if result not in (None, "") else op2
            unique_label = f"{self.current_function}_{label}"
            self.text_section.append(f"    bne {cond_reg}, $zero, {unique_label}  # Si {op1} es verdadero, salta a {label}")
        
        elif op_str in ["iffalse", "if_false", "gotof"]:
            cond_reg = self._load_operand(op1)
            label = result if result not in (None, "") else op2
            unique_label = f"{self.current_function}_{label}"
            self.text_section.append(f"    beq {cond_reg}, $zero, {unique_label}  # Si {op1} es falso, salta a {label}")
        
        # PRINT
        elif op_str == "print":
            value = result if result else op1
            reg = self._load_operand(value)
            self.text_section.append(f"    move $a0, {reg}")
            self.text_section.append("    li $v0, 1  # Print integer")
            self.text_section.append("    syscall")
            self.text_section.append("    li $v0, 4  # Print newline")
            self.text_section.append("    la $a0, newline")
            self.text_section.append("    syscall")
        
        # OBJETOS / CLASES (comentarios)
        elif op_str in ["class", "endclass", "attr", "getattr", "setattr"]:
            self.text_section.append(f"    # {operator} {op1} {op2} {result}")
        
        # TRY / CATCH (comentarios)
        elif op_str in ["try", "catch", "endtry", "end_try", "catch_param"]:
            self.text_section.append(f"    # {operator} {op1} {op2} {result}")
        
        else:
            self.text_section.append(f"    # {operator} {op1} {op2} {result}")
    
    def save_to_file(self, filename="output.asm"):
        """Guarda el código MIPS generado en un archivo."""
        mips_code = self.generate()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(mips_code)
        print(f"✅ Código MIPS guardado en {filename}")
        return filename
    
    def get_mips_code(self):
        """Retorna el código MIPS como string."""
        return self.generate()