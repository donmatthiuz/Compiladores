import subprocess
import os
import tempfile
from typing import Optional, Tuple

class MarsExecutor:
    """
    Ejecutor de código MIPS usando el simulador MARS.
    """
    
    def __init__(self, mars_jar_path: str = "/usr/local/lib/Mars4_5.jar"):
        """
        Inicializa el ejecutor de MARS.
        
        Args:
            mars_jar_path: Ruta al archivo JAR de MARS
        """
        self.mars_jar_path = mars_jar_path
        
        if not os.path.exists(mars_jar_path):
            raise FileNotFoundError(f"MARS JAR no encontrado en: {mars_jar_path}")
    
    def execute_mips(self, mips_code: str, max_steps: int = 1000000) -> Tuple[str, str, int]:
        """
        Ejecuta código MIPS usando MARS.
        
        Args:
            mips_code: Código MIPS a ejecutar
            max_steps: Número máximo de instrucciones a ejecutar
        
        Returns:
            Tuple de (stdout, stderr, código_de_retorno)
        """
        # Crear archivo temporal con el código MIPS
        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as tmp_file:
            tmp_file.write(mips_code)
            tmp_filename = tmp_file.name
        
        try:
            # Ejecutar MARS en modo headless (sin GUI)
            # Parámetros:
            # - nc: No copyright notice
            # - me: Maximum error messages
            # - sm: Start execution at main
            # - se1: Self-modifying code enabled
            command = [
                'java', '-jar', self.mars_jar_path,
                'nc',  # No copyright
                f'{max_steps}',  # Max steps
                tmp_filename
            ]
            
            # Ejecutar el comando
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30  # Timeout de 30 segundos
            )
            
            return result.stdout, result.stderr, result.returncode
            
        except subprocess.TimeoutExpired:
            return "", "Error: Tiempo de ejecución excedido (30s)", 1
        
        except Exception as e:
            return "", f"Error al ejecutar MARS: {str(e)}", 1
        
        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_filename):
                os.remove(tmp_filename)
    
    def assemble_only(self, mips_code: str) -> Tuple[bool, str]:
        """
        Solo ensambla el código MIPS sin ejecutarlo (verifica sintaxis).
        
        Args:
            mips_code: Código MIPS a ensamblar
        
        Returns:
            Tuple de (éxito, mensaje)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as tmp_file:
            tmp_file.write(mips_code)
            tmp_filename = tmp_file.name
        
        try:
            # Usar 'a' flag para assemble only
            command = [
                'java', '-jar', self.mars_jar_path,
                'a',  # Assemble only
                tmp_filename
            ]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, "Ensamblado exitoso"
            else:
                return False, result.stderr or "Error de ensamblado"
                
        except Exception as e:
            return False, f"Error: {str(e)}"
        
        finally:
            if os.path.exists(tmp_filename):
                os.remove(tmp_filename)
    
    def execute_with_input(self, mips_code: str, stdin_input: str = "") -> Tuple[str, str, int]:
        """
        Ejecuta código MIPS con entrada estándar.
        
        Args:
            mips_code: Código MIPS a ejecutar
            stdin_input: Entrada para el programa
        
        Returns:
            Tuple de (stdout, stderr, código_de_retorno)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as tmp_file:
            tmp_file.write(mips_code)
            tmp_filename = tmp_file.name
        
        try:
            command = [
                'java', '-jar', self.mars_jar_path,
                'nc',
                tmp_filename
            ]
            
            result = subprocess.run(
                command,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.stdout, result.stderr, result.returncode
            
        except subprocess.TimeoutExpired:
            return "", "Error: Tiempo de ejecución excedido", 1
        except Exception as e:
            return "", f"Error: {str(e)}", 1
        finally:
            if os.path.exists(tmp_filename):
                os.remove(tmp_filename)


# Ejemplo de uso
if __name__ == "__main__":
    executor = MarsExecutor()
    
    # Código MIPS de ejemplo: imprime "Hello World"
    mips_code = """
.data
    hello: .asciiz "Hello, World!\\n"

.text
.globl main
main:
    # Print string
    li $v0, 4        # syscall 4: print string
    la $a0, hello    # load address of string
    syscall
    
    # Exit
    li $v0, 10       # syscall 10: exit
    syscall
"""
    
    print("Ejecutando código MIPS...")
    stdout, stderr, returncode = executor.execute_mips(mips_code)
    
    print(f"\n=== Salida ===")
    print(stdout)
    
    if stderr:
        print(f"\n=== Errores ===")
        print(stderr)
    
    print(f"\nCódigo de retorno: {returncode}")
    
    # Ejemplo de verificación de sintaxis
    print("\n" + "="*50)
    print("Verificando sintaxis...")
    success, message = executor.assemble_only(mips_code)
    print(f"Resultado: {message}")