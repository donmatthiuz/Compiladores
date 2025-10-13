
## Produccion

docker build -t mi-app-compi .
docker run -it -p 8765:8765 mi-app-compi

## Prueba

docker build -t mi-app-compi2 .
docker run -it -p 8765:8765 mi-app-compi2
