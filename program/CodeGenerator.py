class CodeGenerator:
    """
    Generador de código MIPS con soporte completo para:
    - Tipos: int, float, string, boolean, null, arrays, clases
    - Funciones recursivas con stack frames
    - Etiquetas únicas por función
    """
    
    def __init__(self, quadruple_table, linked_table):
        self.quads = quadruple_table.quadruples
        self.mips_code = []
        self.data_section = []
        self.text_section = []
        self.linked_table = linked_table
        
        # Mapeo de temporales/variables
        self.registers = {}
        self.float_registers = {}  # Para floats
        self.available_regs = [f"$t{i}" for i in range(10)]
        self.available_float_regs = [f"$f{i}" for i in range(4, 20, 2)]  # $f4, $f6, $f8...
        
        # Información de funciones
        self.functions = {}
        self.current_function = "main"
        self.label_counter = 0
        self.function_labels = {}
        
        # Información de arrays
        self.arrays = {}
        self.heap_pointer = 0x10010000
        
        # Strings literales
        self.string_literals = {}
        self.string_counter = 0
        
    def _get_type_from_linked_table(self, name):
        """Obtiene el tipo de una variable desde la LinkedTable."""
        if name is None or name == "":
            return None
            
        # Buscar en la tabla enlazada
        node, type_obj, offset = self.linked_table.resolve_in_scopes(name)
        if type_obj:
            return str(type_obj)  # Convierte Type a string
        
        # Si es temporal, asumir integer por defecto (mejorar con análisis)
        if self._is_temporary(name):
            return "integer"
        
        return None
    
    def _get_register(self, name, is_float=False):
        """Obtiene o asigna un registro (int o float)."""
        if is_float:
            if name in self.float_registers:
                return self.float_registers[name]
            
            for reg in self.available_float_regs:
                if reg not in self.float_registers.values():
                    self.float_registers[name] = reg
                    return reg
            return "$f4"
        else:
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
        s = str(operand)
        # Detectar int, float, bool
        if s in ["true", "false", "null"]:
            return True
        return s.lstrip('-').replace('.', '', 1).isdigit()
    
    def _is_temporary(self, operand):
        if operand is None or operand == "":
            return False
        return str(operand).startswith('t') and str(operand)[1:].isdigit()
    
    def _is_string_literal(self, operand):
        """Detecta si es un string literal (entre comillas)."""
        if operand is None or operand == "":
            return False
        s = str(operand)
        return (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'"))
    
    def _add_string_literal(self, string_value):
        """Agrega un string literal a la sección .data y retorna su etiqueta."""
        # Remover comillas
        clean_string = string_value.strip('"').strip("'")
        
        # Verificar si ya existe
        for label, value in self.string_literals.items():
            if value == clean_string:
                return label
        
        # Crear nueva etiqueta
        label = f"str_{self.string_counter}"
        self.string_counter += 1
        self.string_literals[label] = clean_string
        return label
    
    def _load_operand(self, operand, expected_type=None):
        """
        Carga un operando en un registro según su tipo.
        Retorna (registro, tipo_real).
        """
        if operand is None or operand == "":
            return None, None
        
        # Determinar tipo
        actual_type = expected_type or self._get_type_from_linked_table(operand)
        
        # STRING LITERAL
        if self._is_string_literal(operand):
            label = self._add_string_literal(operand)
            reg = self._get_register(f"str_{label}")
            self.text_section.append(f"    la {reg}, {label}  # Cargar dirección del string")
            return reg, "string"
        
        # CONSTANTES
        if self._is_constant(operand):
            s = str(operand)
            
            # Boolean
            if s == "true":
                reg = self._get_register(f"const_true")
                self.text_section.append(f"    li {reg}, 1  # true")
                return reg, "boolean"
            elif s == "false":
                reg = self._get_register(f"const_false")
                self.text_section.append(f"    li {reg}, 0  # false")
                return reg, "boolean"
            elif s == "null":
                reg = self._get_register(f"const_null")
                self.text_section.append(f"    li {reg}, 0  # null")
                return reg, "null"
            
            # Float
            elif '.' in s:
                reg = self._get_register(f"const_{operand}", is_float=True)
                self.text_section.append(f"    li.s {reg}, {operand}  # float constant")
                return reg, "float"
            
            # Integer
            else:
                reg = self._get_register(f"const_{operand}")
                self.text_section.append(f"    li {reg}, {operand}")
                return reg, "integer"
        
        # TEMPORALES
        if self._is_temporary(operand):
            if actual_type == "float":
                return self._get_register(operand, is_float=True), "float"
            return self._get_register(operand), actual_type or "integer"
        
        # PARÁMETROS EN FUNCIONES
        if self.current_function != "main" and operand in self.functions.get(self.current_function, {}).get('params', []):
            param_index = self.functions[self.current_function]['params'].index(operand)
            
            if actual_type == "float":
                reg = self._get_register(operand, is_float=True)
                self.text_section.append(f"    l.s {reg}, {16 + param_index * 4}($fp)  # float param {operand}")
                return reg, "float"
            else:
                reg = self._get_register(operand)
                self.text_section.append(f"    lw {reg}, {16 + param_index * 4}($fp)  # param {operand}")
                return reg, actual_type or "integer"
        
        # VARIABLES NORMALES
        if actual_type == "float":
            return self._get_register(operand, is_float=True), "float"
        
        return self._get_register(operand), actual_type or "integer"
    
    def generate(self):
        """Genera el código MIPS completo."""
        # Sección .data
        self.data_section.append(".data")
        self.data_section.append("newline: .asciiz \"\\n\"")
        
        # Identificar funciones primero
        self._identify_functions()
        
        # Sección .text
        self.text_section.append("")
        self.text_section.append(".text")
        self.text_section.append(".globl main")
        self.text_section.append("")
        
        # Generar main primero
        self._generate_main()
        
        # Generar funciones después
        self._generate_functions()
        
        # Agregar strings literales al final de .data
        for label, value in self.string_literals.items():
            self.data_section.append(f"{label}: .asciiz \"{value}\"")
        
        self.data_section.append("")
        
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
        
        # Encontrar cuádruplos de main
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
        
        # Generar código
        for quad in main_quads:
            self._translate_quadruple(quad)
        
        # Salir
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
            
            # Stack frame
            self.text_section.append("    addi $sp, $sp, -16")
            self.text_section.append("    sw $ra, 12($sp)")
            self.text_section.append("    sw $fp, 8($sp)")
            self.text_section.append("    move $fp, $sp")
            
            # Guardar parámetros
            for i, param in enumerate(func_info['params']):
                if i < 4:
                    self.text_section.append(f"    sw $a{i}, {16 + i*4}($fp)  # param {param}")
            
            # Cuerpo de la función
            start = func_info['start'] + 1
            end = func_info['end']
            
            for i in range(start, end):
                quad = self.quads[i]
                self._translate_quadruple(quad)
            
            # Cleanup
            self.text_section.append(f"{func_name}_end:")
            self.text_section.append("    lw $ra, 12($sp)")
            self.text_section.append("    lw $fp, 8($sp)")
            self.text_section.append("    addi $sp, $sp, 16")
            self.text_section.append("    jr $ra")
            self.text_section.append("")
            
            self.current_function = "main"
    
    def _translate_quadruple(self, quad):
        """Traduce un cuádruplo a MIPS según el tipo de operación."""
        operator, op1, op2, result = quad
        op_str = str(operator).lower() if operator else ""
        
        # ==================== ARRAYS ====================
        if op_str == "newarr":
            size = int(op1) if op1 else 0
            array_temp = result
            bytes_needed = size * 4
            
            array_reg = self._get_register(array_temp)
            self.text_section.append(f"    # newarr: array[{size}]")
            self.text_section.append(f"    li {array_reg}, {self.heap_pointer}")
            
            self.arrays[array_temp] = {'size': size, 'address': self.heap_pointer}
            self.heap_pointer += bytes_needed
        
        elif op_str == "setelem":
            array_name = op1
            index = op2
            value = result
            
            array_reg = self._get_register(array_name)
            value_reg, value_type = self._load_operand(value)
            
            if self._is_constant(index):
                offset = int(index) * 4
                self.text_section.append(f"    # setelem: {array_name}[{index}] = {value}")
                if value_type == "float":
                    self.text_section.append(f"    s.s {value_reg}, {offset}({array_reg})")
                else:
                    self.text_section.append(f"    sw {value_reg}, {offset}({array_reg})")
            else:
                index_reg, _ = self._load_operand(index)
                temp_reg = "$t9"
                self.text_section.append(f"    # setelem: {array_name}[{index}] = {value}")
                self.text_section.append(f"    sll {temp_reg}, {index_reg}, 2")
                self.text_section.append(f"    add {temp_reg}, {array_reg}, {temp_reg}")
                if value_type == "float":
                    self.text_section.append(f"    s.s {value_reg}, 0({temp_reg})")
                else:
                    self.text_section.append(f"    sw {value_reg}, 0({temp_reg})")
        
        elif op_str == "offset":
            array_name = op1
            index = op2
            result_temp = result
            
            array_reg = self._get_register(array_name)
            index_reg, _ = self._load_operand(index)
            result_reg = self._get_register(result_temp)
            
            self.text_section.append(f"    # offset: {array_name}[{index}]")
            self.text_section.append(f"    sll {result_reg}, {index_reg}, 2")
            self.text_section.append(f"    add {result_reg}, {array_reg}, {result_reg}")
        
        elif op_str == "getelem":
            array_name = op1
            offset_or_index = op2
            result_temp = result
            
            result_type = self._get_type_from_linked_table(result_temp)
            is_float = result_type == "float"
            
            array_reg = self._get_register(array_name)
            result_reg = self._get_register(result_temp, is_float=is_float)
            
            if offset_or_index and str(offset_or_index).startswith('t'):
                offset_reg = self._get_register(offset_or_index)
                self.text_section.append(f"    # getelem")
                if is_float:
                    self.text_section.append(f"    l.s {result_reg}, 0({offset_reg})")
                else:
                    self.text_section.append(f"    lw {result_reg}, 0({offset_reg})")
            else:
                if self._is_constant(offset_or_index):
                    offset = int(offset_or_index) * 4
                    self.text_section.append(f"    # getelem: {array_name}[{offset_or_index}]")
                    if is_float:
                        self.text_section.append(f"    l.s {result_reg}, {offset}({array_reg})")
                    else:
                        self.text_section.append(f"    lw {result_reg}, {offset}({array_reg})")
                else:
                    index_reg, _ = self._load_operand(offset_or_index)
                    temp_reg = "$t9"
                    self.text_section.append(f"    # getelem")
                    self.text_section.append(f"    sll {temp_reg}, {index_reg}, 2")
                    self.text_section.append(f"    add {temp_reg}, {array_reg}, {temp_reg}")
                    if is_float:
                        self.text_section.append(f"    l.s {result_reg}, 0({temp_reg})")
                    else:
                        self.text_section.append(f"    lw {result_reg}, 0({temp_reg})")
        
        # ==================== ASIGNACIÓN ====================
        elif operator == "=":
            src_reg, src_type = self._load_operand(op1)
            if src_reg and result:
                dest_type = self._get_type_from_linked_table(result)
                is_float = dest_type == "float" or src_type == "float"
                
                dest_reg = self._get_register(result, is_float=is_float)
                
                if src_reg != dest_reg:
                    if is_float:
                        self.text_section.append(f"    mov.s {dest_reg}, {src_reg}  # {result} = {op1}")
                    else:
                        self.text_section.append(f"    move {dest_reg}, {src_reg}  # {result} = {op1}")
        
       
        elif operator == "+":
            r1, t1 = self._load_operand(op1)
            r2, t2 = self._load_operand(op2)
            
            # Concatenación de strings
            if t1 == "string" or t2 == "string":
                self.text_section.append(f"    # Concatenación de strings: {result} = {op1} + {op2}")
                
                # Reservar espacio en heap para el resultado
                result_addr = self.heap_pointer
                self.heap_pointer += 256  # 256 bytes para el string concatenado
                
                rd = self._get_register(result)
                
                # Guardar registros r1 y r2 si son necesarios
                self.text_section.append(f"    move $s0, {r1}  # guardar ptr string 1")
                self.text_section.append(f"    move $s1, {r2}  # guardar ptr string 2")
                self.text_section.append(f"    li {rd}, {result_addr}  # dirección destino")
                
                # Copiar primer string
                self.text_section.append(f"    move $t8, {rd}  # ptr destino")
                self.text_section.append(f"    move $t7, $s0  # ptr source 1")
                self.text_section.append(f"{self.current_function}_strcpy1_{self.label_counter}:")
                self.text_section.append(f"    lb $t6, 0($t7)")
                self.text_section.append(f"    beq $t6, $zero, {self.current_function}_strcpy2_{self.label_counter}")
                self.text_section.append(f"    sb $t6, 0($t8)")
                self.text_section.append(f"    addi $t7, $t7, 1")
                self.text_section.append(f"    addi $t8, $t8, 1")
                self.text_section.append(f"    j {self.current_function}_strcpy1_{self.label_counter}")
                
                # Copiar segundo string
                self.text_section.append(f"{self.current_function}_strcpy2_{self.label_counter}:")
                self.text_section.append(f"    move $t7, $s1  # ptr source 2")
                self.text_section.append(f"{self.current_function}_strcpy2_loop_{self.label_counter}:")
                self.text_section.append(f"    lb $t6, 0($t7)")
                self.text_section.append(f"    sb $t6, 0($t8)")
                self.text_section.append(f"    beq $t6, $zero, {self.current_function}_strcat_end_{self.label_counter}")
                self.text_section.append(f"    addi $t7, $t7, 1")
                self.text_section.append(f"    addi $t8, $t8, 1")
                self.text_section.append(f"    j {self.current_function}_strcpy2_loop_{self.label_counter}")
                self.text_section.append(f"{self.current_function}_strcat_end_{self.label_counter}:")
                
                self.label_counter += 1
            
            # Suma de floats
            elif t1 == "float" or t2 == "float":
                is_float = True
                rd = self._get_register(result, is_float=is_float)
                self.text_section.append(f"    add.s {rd}, {r1}, {r2}  # {result} = {op1} + {op2}")
            
            # Suma de enteros
            else:
                rd = self._get_register(result)
                self.text_section.append(f"    add {rd}, {r1}, {r2}  # {result} = {op1} + {op2}")
                
        elif operator == "-":
            r1, t1 = self._load_operand(op1)
            r2, t2 = self._load_operand(op2)
            
            is_float = t1 == "float" or t2 == "float"
            rd = self._get_register(result, is_float=is_float)
            
            if is_float:
                self.text_section.append(f"    sub.s {rd}, {r1}, {r2}  # {result} = {op1} - {op2}")
            else:
                self.text_section.append(f"    sub {rd}, {r1}, {r2}  # {result} = {op1} - {op2}")
        
        elif operator == "*":
            r1, t1 = self._load_operand(op1)
            r2, t2 = self._load_operand(op2)
            
            is_float = t1 == "float" or t2 == "float"
            rd = self._get_register(result, is_float=is_float)
            
            if is_float:
                self.text_section.append(f"    mul.s {rd}, {r1}, {r2}  # {result} = {op1} * {op2}")
            else:
                self.text_section.append(f"    mul {rd}, {r1}, {r2}  # {result} = {op1} * {op2}")
        
        elif operator == "/":
            r1, t1 = self._load_operand(op1)
            r2, t2 = self._load_operand(op2)
            
            is_float = t1 == "float" or t2 == "float"
            rd = self._get_register(result, is_float=is_float)
            
            if is_float:
                self.text_section.append(f"    div.s {rd}, {r1}, {r2}  # {result} = {op1} / {op2}")
            else:
                self.text_section.append(f"    div {r1}, {r2}")
                self.text_section.append(f"    mflo {rd}  # {result} = {op1} / {op2}")
        
        # ==================== COMPARACIONES ====================
        elif operator == "<":
            r1, t1 = self._load_operand(op1)
            r2, t2 = self._load_operand(op2)
            rd = self._get_register(result)
            
            if t1 == "float" or t2 == "float":
                self.text_section.append(f"    c.lt.s {r1}, {r2}")
                self.text_section.append(f"    bc1t {self.current_function}_true_{self.label_counter}")
                self.text_section.append(f"    li {rd}, 0")
                self.text_section.append(f"    j {self.current_function}_end_{self.label_counter}")
                self.text_section.append(f"{self.current_function}_true_{self.label_counter}:")
                self.text_section.append(f"    li {rd}, 1")
                self.text_section.append(f"{self.current_function}_end_{self.label_counter}:")
                self.label_counter += 1
            else:
                self.text_section.append(f"    slt {rd}, {r1}, {r2}  # {result} = ({op1} < {op2})")
        
        elif operator == ">":
            r1, t1 = self._load_operand(op1)
            r2, t2 = self._load_operand(op2)
            rd = self._get_register(result)
            
            if t1 == "float" or t2 == "float":
                self.text_section.append(f"    c.lt.s {r2}, {r1}")
                self.text_section.append(f"    bc1t {self.current_function}_true_{self.label_counter}")
                self.text_section.append(f"    li {rd}, 0")
                self.text_section.append(f"    j {self.current_function}_end_{self.label_counter}")
                self.text_section.append(f"{self.current_function}_true_{self.label_counter}:")
                self.text_section.append(f"    li {rd}, 1")
                self.text_section.append(f"{self.current_function}_end_{self.label_counter}:")
                self.label_counter += 1
            else:
                self.text_section.append(f"    slt {rd}, {r2}, {r1}  # {result} = ({op1} > {op2})")
        
        elif operator in ["<=", ">="]:
            r1, t1 = self._load_operand(op1)
            r2, t2 = self._load_operand(op2)
            rd = self._get_register(result)
            
            if t1 == "float" or t2 == "float":
                comp = "le" if operator == "<=" else "le"
                if operator == ">=":
                    r1, r2 = r2, r1
                self.text_section.append(f"    c.{comp}.s {r1}, {r2}")
                self.text_section.append(f"    bc1t {self.current_function}_true_{self.label_counter}")
                self.text_section.append(f"    li {rd}, 0")
                self.text_section.append(f"    j {self.current_function}_end_{self.label_counter}")
                self.text_section.append(f"{self.current_function}_true_{self.label_counter}:")
                self.text_section.append(f"    li {rd}, 1")
                self.text_section.append(f"{self.current_function}_end_{self.label_counter}:")
                self.label_counter += 1
            else:
                if operator == "<=":
                    self.text_section.append(f"    slt {rd}, {r2}, {r1}")
                    self.text_section.append(f"    xori {rd}, {rd}, 1")
                else:  # >=
                    self.text_section.append(f"    slt {rd}, {r1}, {r2}")
                    self.text_section.append(f"    xori {rd}, {rd}, 1")
        
        elif operator == "==":
            r1, t1 = self._load_operand(op1)
            r2, t2 = self._load_operand(op2)
            rd = self._get_register(result)
            
            if t1 == "float" or t2 == "float":
                self.text_section.append(f"    c.eq.s {r1}, {r2}")
                self.text_section.append(f"    bc1t {self.current_function}_true_{self.label_counter}")
                self.text_section.append(f"    li {rd}, 0")
                self.text_section.append(f"    j {self.current_function}_end_{self.label_counter}")
                self.text_section.append(f"{self.current_function}_true_{self.label_counter}:")
                self.text_section.append(f"    li {rd}, 1")
                self.text_section.append(f"{self.current_function}_end_{self.label_counter}:")
                self.label_counter += 1
            else:
                self.text_section.append(f"    xor {rd}, {r1}, {r2}")
                self.text_section.append(f"    sltiu {rd}, {rd}, 1")
        
        elif operator == "!=":
            r1, t1 = self._load_operand(op1)
            r2, t2 = self._load_operand(op2)
            rd = self._get_register(result)
            
            if t1 == "float" or t2 == "float":
                self.text_section.append(f"    c.eq.s {r1}, {r2}")
                self.text_section.append(f"    bc1f {self.current_function}_true_{self.label_counter}")
                self.text_section.append(f"    li {rd}, 0")
                self.text_section.append(f"    j {self.current_function}_end_{self.label_counter}")
                self.text_section.append(f"{self.current_function}_true_{self.label_counter}:")
                self.text_section.append(f"    li {rd}, 1")
                self.text_section.append(f"{self.current_function}_end_{self.label_counter}:")
                self.label_counter += 1
            else:
                self.text_section.append(f"    xor {rd}, {r1}, {r2}")
                self.text_section.append(f"    sltu {rd}, $zero, {rd}")
        
        # ==================== FUNCIONES ====================
        elif op_str == "call":
            func_name = op1 if op1 else result
            used_regs = [reg for reg in self.registers.values() if reg.startswith('$t')]
            stack_space = len(used_regs) * 4
            
            if stack_space > 0:
                self.text_section.append(f"    addi $sp, $sp, -{stack_space}")
                for i, reg in enumerate(used_regs):
                    self.text_section.append(f"    sw {reg}, {i*4}($sp)")
            
            self.text_section.append(f"    jal {func_name}")
            
            if stack_space > 0:
                for i, reg in enumerate(used_regs):
                    self.text_section.append(f"    lw {reg}, {i*4}($sp)")
                self.text_section.append(f"    addi $sp, $sp, {stack_space}")
            
            if result:
                self.text_section.append(f"    move {self._get_register(result)}, $v0")
        
        elif op_str == "arg":
            arg_value = op1 if op1 else result
            arg_index = int(op2) if op2 else 0
            reg, _ = self._load_operand(arg_value)
            if arg_index < 4:
                self.text_section.append(f"    move $a{arg_index}, {reg}  # arg {arg_index}")
        
        elif op_str == "return":
            return_value = op1 if op1 else result
            if return_value:
                reg, _ = self._load_operand(return_value)
                self.text_section.append(f"    move $v0, {reg}")
            self.text_section.append(f"    j {self.current_function}_end")
        
        # ==================== CONTROL DE FLUJO ====================
        elif op_str == "label":
            label_name = result if result else op1
            unique_label = f"{self.current_function}_{label_name}"
            self.text_section.append(f"{unique_label}:")
        
        elif op_str == "goto":
            label = op1 or result
            unique_label = f"{self.current_function}_{label}"
            self.text_section.append(f"    j {unique_label}")
        
        elif op_str in ["if", "iftrue", "gotot"]:
            cond_reg, _ = self._load_operand(op1)
            label = result if result not in (None, "") else op2
            unique_label = f"{self.current_function}_{label}"
            self.text_section.append(f"    bne {cond_reg}, $zero, {unique_label}")
        
        elif op_str in ["iffalse", "if_false", "gotof"]:
            cond_reg, _ = self._load_operand(op1)
            label = result if result not in (None, "") else op2
            unique_label = f"{self.current_function}_{label}"
            self.text_section.append(f"    beq {cond_reg}, $zero, {unique_label}")
        
        # ==================== PRINT ====================
        elif op_str == "print":
            value = result if result else op1
            
            # Detectar tipo
            value_type = self._get_type_from_linked_table(value)
            
            # String literal
            if self._is_string_literal(value):
                label = self._add_string_literal(value)
                self.text_section.append(f"    # print string: {value}")
                self.text_section.append(f"    la $a0, {label}")
                self.text_section.append("    li $v0, 4  # Print string")
                self.text_section.append("    syscall")
            
            # Float
            elif value_type == "float":
                reg, _ = self._load_operand(value)
                self.text_section.append(f"    # print float: {value}")
                self.text_section.append(f"    mov.s $f12, {reg}")
                self.text_section.append("    li $v0, 2  # Print float")
                self.text_section.append("    syscall")
                self.text_section.append("    li $v0, 4  # Print newline")
                self.text_section.append("    la $a0, newline")
                self.text_section.append("    syscall")
            
            # String variable
            elif value_type == "string":
                reg, _ = self._load_operand(value)
                self.text_section.append(f"    # print string: {value}")
                self.text_section.append(f"    move $a0, {reg}")
                self.text_section.append("    li $v0, 4  # Print string")
                self.text_section.append("    syscall")
            
            # Boolean
            elif value_type == "boolean":
                reg, _ = self._load_operand(value)
                self.text_section.append(f"    # print boolean: {value}")
                self.text_section.append(f"    move $a0, {reg}")
                self.text_section.append("    li $v0, 1  # Print int (0/1)")
                self.text_section.append("    syscall")
                self.text_section.append("    li $v0, 4  # Print newline")
                self.text_section.append("    la $a0, newline")
                self.text_section.append("    syscall")
            
            # Integer (default)
            else:
                reg, _ = self._load_operand(value)
                self.text_section.append(f"    # print integer: {value}")
                self.text_section.append(f"    move $a0, {reg}")
                self.text_section.append("    li $v0, 1  # Print integer")
                self.text_section.append("    syscall")
                self.text_section.append("    li $v0, 4  # Print newline")
                self.text_section.append("    la $a0, newline")
                self.text_section.append("    syscall")
        
        # ==================== CLASES / OBJETOS ====================
        elif op_str in ["class", "endclass", "attr", "getattr", "setattr"]:
            self.text_section.append(f"    # {operator} {op1} {op2} {result}")
        
        # ==================== MANEJO DE EXCEPCIONES ====================
        elif op_str in ["try", "catch", "endtry", "end_try", "catch_param"]:
            self.text_section.append(f"    # {operator} {op1} {op2} {result}")
        
        # ==================== OPERACIONES LÓGICAS ====================
        elif operator == "and" or operator == "&&":
            r1, _ = self._load_operand(op1)
            r2, _ = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    and {rd}, {r1}, {r2}  # {result} = {op1} && {op2}")
        
        elif operator == "or" or operator == "||":
            r1, _ = self._load_operand(op1)
            r2, _ = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    or {rd}, {r1}, {r2}  # {result} = {op1} || {op2}")
        
        elif operator == "not" or operator == "!":
            r1, _ = self._load_operand(op1)
            rd = self._get_register(result)
            self.text_section.append(f"    xori {rd}, {r1}, 1  # {result} = !{op1}")
        
        # ==================== MÓDULO ====================
        elif operator == "%":
            r1, _ = self._load_operand(op1)
            r2, _ = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    div {r1}, {r2}  # {op1} % {op2}")
            self.text_section.append(f"    mfhi {rd}  # {result} = resto")
        
        # ==================== POTENCIA (si existe) ====================
        elif operator == "**" or operator == "^":
            r1, _ = self._load_operand(op1)
            r2, _ = self._load_operand(op2)
            rd = self._get_register(result)
            self.text_section.append(f"    # Potencia {op1} ** {op2}")
            self.text_section.append(f"    # TODO: Implementar con loop o función")
            self.text_section.append(f"    move {rd}, {r1}  # Placeholder")
        
        # ==================== CONVERSIÓN DE TIPOS ====================
        elif op_str == "int_to_float":
            r1, _ = self._load_operand(op1)
            rd = self._get_register(result, is_float=True)
            self.text_section.append(f"    mtc1 {r1}, {rd}  # Mover int a coprocesador")
            self.text_section.append(f"    cvt.s.w {rd}, {rd}  # Convertir a float")
        
        elif op_str == "float_to_int":
            r1, _ = self._load_operand(op1)
            rd = self._get_register(result)
            temp_float = "$f0"
            self.text_section.append(f"    cvt.w.s {temp_float}, {r1}  # Convertir a int")
            self.text_section.append(f"    mfc1 {rd}, {temp_float}  # Mover a registro")
        
        # ==================== OPERACIONES NO RECONOCIDAS ====================
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