from MarsExecutor import MarsExecutor

executor = MarsExecutor()

# ============================================
# EJEMPLO 1: Calculadora simple (suma y resta)
# ============================================
print("="*50)
print("EJEMPLO 1: Calculadora Simple")
print("="*50)

mips_calc = """
.data
    prompt1: .asciiz "Calculando: 15 + 27 - 8 = "
    newline: .asciiz "\\n"

.text
.globl main
main:
    # Imprimir prompt
    li $v0, 4
    la $a0, prompt1
    syscall
    
    # Calcular: 15 + 27 - 8
    li $t0, 15
    li $t1, 27
    li $t2, 8
    
    add $t3, $t0, $t1    # t3 = 15 + 27 = 42
    sub $t3, $t3, $t2    # t3 = 42 - 8 = 34
    
    # Imprimir resultado
    li $v0, 1
    move $a0, $t3
    syscall
    
    # Newline
    li $v0, 4
    la $a0, newline
    syscall
    
    # Exit
    li $v0, 10
    syscall
"""

stdout, stderr, returncode = executor.execute_mips(mips_calc)
print(stdout)
if stderr: print("ERROR:", stderr)

# ============================================
# EJEMPLO 2: Factorial de 5
# ============================================
print("\\n" + "="*50)
print("EJEMPLO 2: Factorial de 5")
print("="*50)

mips_factorial = """
.data
    msg: .asciiz "Factorial de 5 = "
    newline: .asciiz "\\n"

.text
.globl main
main:
    # Imprimir mensaje
    li $v0, 4
    la $a0, msg
    syscall
    
    # Calcular factorial de 5
    li $t0, 5          # n = 5
    li $t1, 1          # resultado = 1
    
factorial_loop:
    beq $t0, $zero, print_result
    mul $t1, $t1, $t0  # resultado *= n
    subi $t0, $t0, 1   # n--
    j factorial_loop
    
print_result:
    # Imprimir resultado (120)
    li $v0, 1
    move $a0, $t1
    syscall
    
    # Newline
    li $v0, 4
    la $a0, newline
    syscall
    
    # Exit
    li $v0, 10
    syscall
"""

stdout, stderr, returncode = executor.execute_mips(mips_factorial)
print(stdout)
if stderr: print("ERROR:", stderr)

# ============================================
# EJEMPLO 3: Array - Suma de elementos
# ============================================
print("\\n" + "="*50)
print("EJEMPLO 3: Suma de Array [10, 20, 30, 40, 50]")
print("="*50)

mips_array = """
.data
    array: .word 10, 20, 30, 40, 50
    size: .word 5
    msg1: .asciiz "Elementos: "
    msg2: .asciiz "\\nSuma total: "
    space: .asciiz " "
    newline: .asciiz "\\n"

.text
.globl main
main:
    # Imprimir "Elementos: "
    li $v0, 4
    la $a0, msg1
    syscall
    
    # Inicializar
    la $t0, array      # dirección base del array
    lw $t1, size       # tamaño del array
    li $t2, 0          # índice
    li $t3, 0          # suma acumulada
    
print_loop:
    beq $t2, $t1, calculate_sum
    
    # Cargar elemento actual
    lw $t4, 0($t0)
    
    # Imprimir elemento
    li $v0, 1
    move $a0, $t4
    syscall
    
    # Imprimir espacio
    li $v0, 4
    la $a0, space
    syscall
    
    # Acumular suma
    add $t3, $t3, $t4
    
    # Siguiente elemento
    addi $t0, $t0, 4   # siguiente word (4 bytes)
    addi $t2, $t2, 1   # índice++
    j print_loop

calculate_sum:
    # Imprimir mensaje de suma
    li $v0, 4
    la $a0, msg2
    syscall
    
    # Imprimir suma total
    li $v0, 1
    move $a0, $t3
    syscall
    
    # Newline
    li $v0, 4
    la $a0, newline
    syscall
    
    # Exit
    li $v0, 10
    syscall
"""

stdout, stderr, returncode = executor.execute_mips(mips_array)
print(stdout)
if stderr: print("ERROR:", stderr)

# ============================================
# EJEMPLO 4: Condicionales - Mayor de dos números
# ============================================
print("\\n" + "="*50)
print("EJEMPLO 4: Mayor entre 42 y 37")
print("="*50)

mips_conditional = """
.data
    num1: .word 42
    num2: .word 37
    msg1: .asciiz "Comparando 42 y 37\\n"
    msg2: .asciiz "El mayor es: "
    newline: .asciiz "\\n"

.text
.globl main
main:
    # Imprimir mensaje inicial
    li $v0, 4
    la $a0, msg1
    syscall
    
    # Cargar números
    lw $t0, num1       # t0 = 42
    lw $t1, num2       # t1 = 37
    
    # Comparar
    bgt $t0, $t1, first_is_greater
    move $t2, $t1      # num2 es mayor
    j print_result
    
first_is_greater:
    move $t2, $t0      # num1 es mayor
    
print_result:
    # Imprimir mensaje
    li $v0, 4
    la $a0, msg2
    syscall
    
    # Imprimir el mayor
    li $v0, 1
    move $a0, $t2
    syscall
    
    # Newline
    li $v0, 4
    la $a0, newline
    syscall
    
    # Exit
    li $v0, 10
    syscall
"""

stdout, stderr, returncode = executor.execute_mips(mips_conditional)
print(stdout)
if stderr: print("ERROR:", stderr)

# ============================================
# EJEMPLO 5: Fibonacci (primeros 10 números)
# ============================================
print("\\n" + "="*50)
print("EJEMPLO 5: Secuencia de Fibonacci")
print("="*50)

mips_fibonacci = """
.data
    msg: .asciiz "Fibonacci (10 números): "
    space: .asciiz " "
    newline: .asciiz "\\n"

.text
.globl main
main:
    # Imprimir mensaje
    li $v0, 4
    la $a0, msg
    syscall
    
    # Inicializar
    li $t0, 0          # fib(n-2)
    li $t1, 1          # fib(n-1)
    li $t2, 10         # contador
    
    # Imprimir primer número (0)
    li $v0, 1
    move $a0, $t0
    syscall
    
    li $v0, 4
    la $a0, space
    syscall
    
fib_loop:
    beq $t2, 1, done
    
    # Imprimir fib(n-1)
    li $v0, 1
    move $a0, $t1
    syscall
    
    # Espacio
    li $v0, 4
    la $a0, space
    syscall
    
    # Calcular siguiente
    add $t3, $t0, $t1  # fib(n) = fib(n-1) + fib(n-2)
    move $t0, $t1      # fib(n-2) = fib(n-1)
    move $t1, $t3      # fib(n-1) = fib(n)
    
    # Decrementar contador
    subi $t2, $t2, 1
    j fib_loop

done:
    # Newline
    li $v0, 4
    la $a0, newline
    syscall
    
    # Exit
    li $v0, 10
    syscall
"""

stdout, stderr, returncode = executor.execute_mips(mips_fibonacci)
print(stdout)
if stderr: print("ERROR:", stderr)

print("\\n" + "="*50)
print("TODOS LOS EJEMPLOS COMPLETADOS ✓")
print("="*50)