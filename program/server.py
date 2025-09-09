import asyncio
import websockets
import subprocess
import shlex

async def run_command(command: str) -> str:
    try:
        # Divide el comando en tokens seguros
        args = shlex.split(command)
        # Ejecuta el comando en la terminal actual
        result = subprocess.run(args, capture_output=True, text=True)
        output = result.stdout + result.stderr
        return output.strip() if output else "(no output)"
    except Exception as e:
        return f"Error ejecutando comando: {e}"

async def handler(websocket):
    async for message in websocket:
        output = await run_command(message)
        await websocket.send(output)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Servidor WebSocket escuchando en ws://localhost:8765")
        await asyncio.Future()  # correr para siempre

if __name__ == "__main__":
    asyncio.run(main())
