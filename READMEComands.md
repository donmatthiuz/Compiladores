
## Docker


### Construccion
docker build -t produccion .

### Reconstruccion
docker build --no-cache -t produccion .

### 1. ENTRAR AL BASH (para pruebas/debugging)
docker run -it --rm produccion bash

### 2. EJECUTAR EL SERVIDOR (modo producción)
docker run -it -p 8765:8765 -v ./program:/program produccion

### 3. ENTRAR AL BASH CON VOLUMEN MONTADO (para desarrollo)
docker run -it --rm -p 8765:8765 -v ./program:/program produccion bash

