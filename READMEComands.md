
## Produccion

docker build -t mi-app-compi1 -f Docker2File .
docker run -it -p 8765:8765 mi-app-compi1

## Prueba

docker build -t mi-app-compi .
docker run -it \
  -p 8765:8765 \
  -v ./program:/program \
  mi-app-compi
