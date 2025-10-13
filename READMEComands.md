
## Produccion

docker build -t mi-app-compi1 -f Docker2File .
docker run -it -p 8765:8765 mi-app-compi1

## Prueba

docker build -t mi-app-compi2 .
docker run -it -p 8765:8765 mi-app-compi2
