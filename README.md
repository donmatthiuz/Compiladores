

# 📘 Proyecto 1 – Compiladores

Este proyecto implementa el lenguaje **CompiScript** usando **ANTLR4** y **Python**, con un **IDE web** en **Next.js** para pruebas interactivas.

---

## 👥 Integrantes

* Marlon Hernández – 15177
* Mathew Cordero – 22982

---

## 🐳 Ejecución con Docker

El proyecto incluye **dos configuraciones Docker**:

1. **Dockerfile de pruebas manuales** → sirve para entrar al contenedor y ejecutar comandos a mano.
2. **Dockerfile funcional (principal)** → es el que debe usarse para correr el compilador automáticamente.

   > ⚠️ Copia el contenido de `Docker2File` dentro de tu `Dockerfile` principal antes de construir la imagen.

---

### 1. Construir la imagen

Desde la raíz del proyecto:

```bash
docker build -t compiscript:latest .
```

---

### 2. Levantar el contenedor de forma automática (Docker funcional)

Este arranca el compilador/servidor definido en `server.py`:

```bash
docker run -p 8765:8765 --rm compiscript:latest
```

* Expone el puerto `8765`.
* Ejecuta directamente el comando por defecto:

```bash
CMD ["python3", "-u", "server.py"]
```

---

### 3. Levantar el contenedor en modo manual (solo pruebas)

Si quieres abrir una shell dentro del contenedor para compilar gramáticas o ejecutar programas a mano:

```bash
docker run -it --rm -p 8765:8765 -v "$(pwd)/program":/program compiscript:latest bash
```

Esto te deja en `/program`, con acceso al compilador y la gramática.

---

## ⚙️ Compilar la gramática manualmente

Dentro del contenedor (modo pruebas):

```bash
antlr -Dlanguage=Python3 -visitor CompiScript.g4
```

Esto genera:

* `CompiScriptLexer.py`
* `CompiScriptParser.py`
* `CompiScriptVisitor.py`
* `CompiScriptListener.py`

---

## ▶️ Ejecutar un programa en CompiScript (modo pruebas)

Ejecuta el intérprete con un archivo `.cps`:

```bash
python3 Driver.py program.cps
```

Ejemplo:

```bash
root@<container_id>:/program# python3 Driver.py program.cps
```

---

## 💻 Ejecutar el IDE (Next.js)

El proyecto incluye un **IDE web** para escribir y ejecutar código en CompiScript.

### 1. Ir a la carpeta del IDE

```bash
cd ide
```

### 2. Instalar dependencias

```bash
npm install
```

### 3. Levantar el servidor de desarrollo

```bash
npm run dev
```

### 4. Abrir en el navegador

👉 [http://localhost:3000](http://localhost:3000)

---

## 📂 Estructura del proyecto

```text
.
├── Dockerfile                        # Imagen principal (copiar contenido de Docker2File aquí)
├── Docker2File                       # Docker funcional (para producción)
├── README.md                         # Este archivo
├── README.listener.md                 # Notas sobre listener
├── README_DOCKER.md                   # Notas sobre Docker
├── README_NOTES.md                    # Notas adicionales
├── antlr-4.13.1-complete.jar          # ANTLR local (Java)
├── commands/                          # Scripts de ayuda
│   ├── antlr                          # Alias para antlr
│   └── grun                           # Alias para grun (TestRig)
├── ide/                               # IDE web (Next.js + React + Tailwind)
│   ├── app/                           # Páginas principales
│   ├── components/                    # Componentes UI (editor, terminal, etc.)
│   ├── hooks/                         # Hooks personalizados
│   ├── lib/                           # Utilidades
│   ├── public/                        # Recursos estáticos
│   ├── styles/                        # CSS global
│   ├── package.json                   # Dependencias del IDE
│   └── tsconfig.json                  # Configuración TypeScript
├── program/                           # Compilador en Python + gramática
│   ├── CompiScript.g4                 # Gramática ANTLR
│   ├── CompiScriptLexer.py            # Lexer generado
│   ├── CompiScriptParser.py           # Parser generado
│   ├── CompiScriptVisitor.py          # Visitor generado
│   ├── CompiScriptListener.py         # Listener generado
│   ├── Driver.py                      # Entrada principal del compilador
│   ├── SymbolTable.py                 # Tabla de símbolos
│   ├── custom_types.py                # Sistema de tipos
│   ├── type_check_visitor.py          # Chequeo semántico
│   ├── server.py                      # Servidor del compilador
│   ├── program.cps                    # Programa de ejemplo en CompiScript
│   └── __pycache__/                   # Archivos compilados de Python
├── python-venv.sh                     # Script para crear entorno virtual
└── requirements.txt                   # Dependencias de Python
```

---

## 🛠️ Requisitos previos

* **Docker** instalado
* **Node.js + npm** (para el IDE web)
* **ANTLR4** (ya incluido en el contenedor)

---

## 📝 Ejemplo de programa (`program.cps`)

```cps
// Constante global
const PI: integer = 314;
let greeting: string = "Hello, Compiscript!";
let flag: boolean;

// Array de enteros
let numbers: integer[] = [1, 2, 3, 4, 5];

// Función recursiva
function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

print("Factorial de 5 = " + factorial(5));
```




