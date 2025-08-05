
# Resumen


# Demostración de Funcionamiento 

![alt text](image.png)


# [Link al Video](https://youtu.be/2ocXABxgOog)



# Analisis de Archivos

## Archivos generados por `MiniLang.g4`

| Archivo               | Tipo      | Descripción                                   |
| --------------------- | --------- | --------------------------------------------- |
| `MiniLangLexer.py`    | Tokenizer | Convierte la entrada en tokens.               |
| `MiniLangParser.py`   | Parser    | Reconoce la estructura gramatical.            |
| `MiniLangListener.py` | Listener  | Callbacks vacíos (uno por cada etiqueta `#`). |

---

## Contenido de `MiniLang.g4`

```antlr
grammar MiniLang;

prog  : stat+ ; // reglas de parser (minúscula = regla, mayúscula = token)

stat  : expr NEWLINE             # printExpr
      | ID '=' expr NEWLINE     # assign
      | NEWLINE                 # blank
      ;

expr  : expr ('*'|'/') expr     # MulDiv
      | expr ('+'|'-') expr     # AddSub
      | INT                     # int
      | ID                      # id
      | '(' expr ')'            # parens
      ;

// reglas léxicas (tokens)
MUL : '*' ;
DIV : '/' ;
ADD : '+' ;
SUB : '-' ;
ID  : [a-zA-Z]+ ;
INT : [0-9]+ ;
NEWLINE : '\r'? '\n' ;
WS  : [ \t]+ -> skip ;
```

---

### Reglas del Parser

* Empiezan en **minúscula**.
* Describen la **sintaxis** del lenguaje (generan el AST).

### Reglas Léxicas

* Empiezan en **mayúscula**.
* Definen los **tokens** usando expresiones regulares.

### Etiquetas `#`

* Nombran cada alternativa.
* ANTLR crea **subclases de contexto** (como `MulDivContext`, `AssignContext`, etc.).
* Estas subclases pueden ser utilizadas en el **listener**.

---


# MiniLang.g4

ANTLR genera automáticamente varios archivos que conforman el compilador o intérprete básico del lenguaje definido. Aquí explicamos el propósito de los principales archivos generados:

---

##  MiniLangLexer.py

### ¿Qué hace?

Este archivo contiene el **analizador léxico (lexer)**. Su tarea es **leer el texto de entrada** y **convertirlo en una secuencia de tokens**, que son las unidades mínimas del lenguaje, como palabras clave, identificadores, operadores, etc.

### Características principales:

* Define tokens como:

  * `MUL` para `*`
  * `DIV` para `/`
  * `ADD` para `+`
  * `SUB` para `-`
  * `ID` para identificadores (letras)
  * `INT` para números
  * `NEWLINE` para saltos de línea
  * `WS` para espacios y tabulaciones (que se omiten con `-> skip`)

* Contiene una función `serializedATN()` que representa internamente la gramática como una red de autómatas (típico en lexers de ANTLR).

* Hereda de `Lexer` de `antlr4`.

* Usa `LexerATNSimulator` para interpretar el flujo de tokens.

---

## MiniLangParser.py

### ¿Qué hace?

Contiene el **parser (analizador sintáctico)** que toma los tokens del lexer y **valida si siguen la estructura definida en la gramática**. También **construye el árbol de análisis sintáctico (parse tree)**.

* Aplica las reglas como `prog`, `stat`, `expr`.
* Cada alternativa con etiqueta `#` genera una clase de contexto específica:

  * `PrintExprContext`
  * `AssignContext`
  * `AddSubContext`
  * `MulDivContext`, etc.

---

## MiniLangListener.py

### ¿Qué hace?

Es un **listener base**. Define **métodos vacíos de entrada y salida (`enter` / `exit`) para cada regla etiquetada** en el archivo `.g4`.

### ¿Para qué sirve?

* Puedes **heredar de esta clase** y sobrescribir los métodos que necesitas.
* Se usa junto con `ParseTreeWalker` para **recorrer el árbol de análisis sintáctico** y realizar acciones como evaluar expresiones, guardar variables, etc.

### Ejemplos de métodos definidos:

```python
def enterAssign(self, ctx:MiniLangParser.AssignContext):
    pass

def exitAssign(self, ctx:MiniLangParser.AssignContext):
    pass
```

* Se ejecutan al **entrar o salir** de nodos específicos del árbol.
* Si quieres imprimir o evaluar expresiones, puedes crear una subclase como `EvalListener` y escribir la lógica ahí.

---

##  `Driver.py`*

Este archivo **no lo genera ANTLR** pero se usa para **unir todo**. Suele incluir:

```python
lexer = MiniLangLexer(input_stream)
tokens = CommonTokenStream(lexer)
parser = MiniLangParser(tokens)
tree = parser.prog()

walker = ParseTreeWalker()
listener = EvalListener()
walker.walk(listener, tree)
```

Flujo:

1. Lee el archivo fuente.
2. Crea tokens con el lexer.
3. Valida la sintaxis con el parser.
4. Recorre el árbol con el listener.
5. Ejecuta la lógica definida en tu clase `EvalListener`.

---

## La grafica del mismo seria asi

```text
┌────────────────────┐
│ Archivo de entrada │
└─────────┬──────────┘
          ↓
┌────────────────────┐
│  MiniLangLexer.py  │ ← Tokenizer
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ MiniLangParser.py  │ ← Parser (AST)
└─────────┬──────────┘
          ↓
┌────────────────────────┐
│ MiniLangListener.py    │ ← Callbacks vacíos
├────────────────────────┤
│ EvalListener (personal)│ ← Tu lógica va aquí
└────────────────────────┘
          ↓
┌────────────────────┐
│     Driver.py      │ ← Ejecuta el flujo
└────────────────────┘
```

## Listener 

Un Listener en ANTLR es una clase que permite escuchar eventos que ocurren durante el recorrido del árbol sintáctico generado por el parser. Por cada regla del parser, ANTLR genera métodos como enterRegla y exitRegla, que se pueden sobreescribir en el Listener para ejecutar acciones personalizadas cuando se entra o sale de una regla.


#### ¿Cómo se usa un Listener en el `Driver.py`?

En tu archivo `Driver.py`, defines una clase llamada `EvalListener` que hereda de `MiniLangListener` (generado automáticamente por ANTLR a partir de tu gramática). Este listener se encarga de evaluar el código interpretado.

```python
class EvalListener(MiniLangListener):
    def __init__(self):
        self.vars = {}
```

Aqui se inicia un diccionario que guarda variables

```python
def exitAssign(self, ctx):
    var_name = ctx.ID().getText()
    value = self.evalExpr(ctx.expr())
    self.vars[var_name] = value
```

Cuando el parser detecta una asignación (por ejemplo, `a = 5`), este método se activa al **salir** de la regla `assign`. Se evalúa la expresión y se guarda el valor en `self.vars`.

```python
def exitPrintExpr(self, ctx):
    value = self.evalExpr(ctx.expr())
    print(value)
```

Este se ejecuta cuando se encuentra una instrucción de impresión. Evalúa la expresión y la imprime.

---

#### ¿Cómo se conecta el Listener al análisis?

En la función `main()`:

```python
walker = ParseTreeWalker()
listener = EvalListener()
walker.walk(listener, tree)
```

Se recorre el árbol sintáctico (`tree`) con un `ParseTreeWalker`, que **llama automáticamente** a los métodos `exitAssign`, `exitPrintExpr`, etc., del `EvalListener`, ejecutando así la lógica de evaluación.

## Archivos de tokenizacion



### MiniLang.interp

* Describe **las reglas y transiciones internas** que el parser debe seguir para reconocer el lenguaje definido en `MiniLang.g4`.
* Contiene las definiciones de:

  * **Tokens** (símbolos terminales, como operadores, identificadores, números).
  * **Reglas del parser** (estructuras sintácticas como expresiones, instrucciones).
* Permite que un intérprete ANTLR (por ejemplo, en modo interactivo o de pruebas) pueda:

  * Recorrer el código fuente de entrada.
  * Identificar correctamente los tokens y las reglas aplicables.
  * Detectar errores de sintaxis o procesar árboles sintácticos.

---

#### Estructura general del archivo

-  1. **Token Literal Names**

Lista los símbolos literales de los tokens, como `'='`, `'('`, `')'`, `'*'`, `'/'`, `'+'`, `'-'`.

Estos son los caracteres o cadenas que el lexer reconocerá exactamente.

- 2. **Token Symbolic Names**

Son los nombres simbólicos que representan categorías de tokens, por ejemplo:

  * `MUL` (multiplicación)
  * `DIV` (división)
  * `ADD` (suma)
  * `SUB` (resta)
  * `ID` (identificador)
  * `INT` (número entero)
  * `NEWLINE` (salto de línea)
  * `WS` (espacios en blanco, ignorados)

- 3. **Rule Names**

Nombres de las reglas de la gramática, como:

  * `prog` (programa)
  * `stat` (sentencia)
  * `expr` (expresión)

-  4. **ATN (Abstract Transition Network)**

Lista numérica muy larga que codifica el autómata interno.

Este autómata es el que guía al parser en cómo avanzar y qué reglas aplicar en función del texto de entrada.

Contiene estados, transiciones, decisiones, predicados, y demás información para que el parser se ejecute correctamente.

```
atn:
[4, 1, 11, 43, ......]
```

---

### MiniLang.tokens

Es un archivo **generado automáticamente por ANTLR** cuando compilas una gramática `.g4`. Contiene una **lista de tokens léxicos**, que son las unidades mínimas del lenguaje que ANTLR reconoce en el análisis léxico. 

Tambien genera otro archivo llamado  **MiniLangLexer.tokens** que son los tokens del Lexer 

Cada línea sigue el formato:

```
NOMBRE_DEL_TOKEN=VALOR_ENTERO
```

Por ejemplo:

```
MUL=4      // representa el token '*'
ID=8       // representa un identificador (variable)
T__0=1     // representa un símbolo como '=' cuando no se le dio un nombre
```

---

#### **¿Para qué sirve?**

* Asocia **nombres de tokens** con **números internos** usados por el parser.
* Es usado internamente por ANTLR para identificar tokens durante el análisis.
* Útil para herramientas de depuración o cuando quieres saber qué número representa cada token.

---

#### Nota importante:

* Los tokens como `'='`, `'('`, `')'` que se escriben **directamente entre comillas** en la gramática no reciben nombres personalizados. ANTLR les asigna nombres automáticos como `T__0`, `T__1`, etc.
* Los tokens con nombre propio como `MUL`, `ID`, `INT`, sí se definen manualmente en la gramática (`MUL: '*';` por ejemplo).

---


### program_test.txt

Este archivo unicamente contiene un ejemplo del uso del lenguaje

```
5 * 5
a = 4
b = 6
c = a + b
c
```

El resultado deberia ser de  25, 10 ya que como se definio en el Driver.py es que al solo colocar la variable , la captura y la imprime


### fail_test#.txt
Aqui se almacenan los errores cometidos. Especificamente en que token fue el error, asi describiendo el error que ocurre. Ejemplo

```
7+
```

Aqui el 7 +   no tiene el siguiente numero que deberia estar tras un + .