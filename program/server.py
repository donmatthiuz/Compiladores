import asyncio
import websockets
import subprocess
import tempfile
import os

async def run_code(code: str, extension: str) -> str:
    try:
        # Crear un archivo temporal que se sobreescriba siempre
        filename = f"temp_code.{extension}"
        with open(filename, "w") as f:
            f.write(code)
        
        # Ejecutar el comando
        command = ["python3", "Driver.py", filename]
        result = subprocess.run(command, capture_output=True, text=True)
        output = result.stdout + result.stderr

        # Opcional: borrar el archivo si quieres que no quede
        # os.remove(filename)

        return output.strip() if output else "(no output)"
    except Exception as e:
        return f"Error ejecutando código: {e}"

async def handler(websocket):
    async for message in websocket:
        # Se espera un formato simple "EXTENSION\nCODIGO"
        try:
            extension, code = message.split("\n", 1)
        except ValueError:
            await websocket.send("Formato incorrecto. Usa: EXTENSION\\nCODIGO")
            continue

        output = await run_code(code, extension)
        await websocket.send(output)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Servidor WebSocket escuchando en ws://localhost:8765")
        await asyncio.Future()  # correr para siempre

if __name__ == "__main__":
    asyncio.run(main())
