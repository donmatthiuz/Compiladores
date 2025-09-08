

# 📘 Proyecto 1 – Compiladores

Este proyecto implementa el lenguaje **CompiScript** usando **ANTLR4** y **Python**, con un **IDE web** en **Next.js** para pruebas interactivas.

---

## 🐳 Ejecución con Docker

### 1. Construir la imagen de Docker

Desde la raíz del proyecto:

```bash
docker build --rm -t compiscript-image .
```

### 2. Levantar el contenedor

```bash
sudo docker run -it --rm -v "$(pwd)/program":/program compiscript-image bash
```

Esto abrirá una shell dentro del contenedor con la carpeta `program/` montada.

---

## ⚙️ Compilar la gramática

Dentro del contenedor, genera el lexer, parser y visitor:

```bash
antlr -Dlanguage=Python3 -visitor CompiScript.g4
```

Esto creará los archivos:

* `CompiScriptLexer.py`
* `CompiScriptParser.py`
* `CompiScriptVisitor.py`
* `CompiScriptListener.py`

---

## ▶️ Ejecutar un programa en CompiScript

Para probar un script escrito en `.cps`:

```bash
python3 Driver.py program.cps
```

Ejemplo en la shell del contenedor:

```bash
root@<container_id>:/program# python3 Driver.py program.cps
```

---

## 💻 Ejecutar el IDE

El proyecto incluye un **IDE web** en Next.js para editar y ejecutar código en CompiScript.

### 1. Ir a la carpeta `ide`

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

Ir a 👉 [http://localhost:3000](http://localhost:3000)

---

## 📂 Estructura del proyecto

```text
.
├── Dockerfile                        # Imagen Docker del compilador
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
│   ├── public/                        # Recursos estáticos (imágenes, íconos)
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
│   ├── custom_types.py                # Sistema de tipos (integer, string, etc.)
│   ├── type_check_visitor.py          # Chequeo semántico con Visitor
│   ├── program.cps                    # Programa de ejemplo en CompiScript
│   └── __pycache__/                   # Archivos compilados de Python
├── python-venv.sh                     # Script para crear entorno virtual
└── requirements.txt                   # Dependencias de Python
```

---

## 🛠️ Requisitos previos

* **Docker** instalado
* **Node.js + npm** (para el IDE web)
* **ANTLR4** (ya viene en el contenedor si usas Docker)

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

---

👉 Con este README, ya tienes **instrucciones claras para ejecutar el compilador, levantar el IDE y entender la estructura del proyecto**.

