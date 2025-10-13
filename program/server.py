import asyncio
import websockets
import subprocess

async def run_code(code: str, extension: str, mode: str = "debug") -> str:
    try:
        filename = f"temp_code.{extension}"
        with open(filename, "w") as f:
            f.write(code)

        # Pasar el modo como segundo argumento a Driver.py
        
        command = ["python3", "Driver.py", filename, mode]
        result = subprocess.run(command, capture_output=True, text=True)
        output = result.stdout + result.stderr

        return output.strip() if output else "(no output)"
    except Exception as e:
        return f"Error ejecutando código: {e}"

async def handler(websocket):
    async for message in websocket:
        try:
            # Intentamos separar header y código
            header, code = message.split("\n", 1)
            if "|" in header:
                extension, mode = header.split("|", 1)
            else:
                extension = header
                mode = "debug"
        except ValueError:
            await websocket.send("Formato incorrecto. Usa: EXTENSION|MODO\\nCODIGO o EXTENSION\\nCODIGO")
            continue

        output = await run_code(code, extension, mode)
        await websocket.send(output)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Servidor WebSocket escuchando en ws://localhost:8765")
        await asyncio.Future()  # correr para siempre

if __name__ == "__main__":
    asyncio.run(main())
