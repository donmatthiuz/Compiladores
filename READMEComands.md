
## Produccion

docker build -t produccion -f Docker2File .
docker run -it -p 8765:8765 -v ./program:/program produccion


## Prueba

docker build -t dev .
docker run -it -p 8765:8765 -v ./program:/program dev
