import asyncio, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

async def shell():
    try:
        reader, writer = await asyncio.open_connection('localhost', 4000)
        print('CONNECTED TO MUD')
        writer.write(b'connect Antigravity agentpass\n')
        await writer.drain()
        
        # Read loop
        async def read_stream():
            while True:
                data = await reader.read(8192)
                if not data: break
                text = data.decode('utf-8', errors='replace')
                text = re.sub(r'\x1b\[[0-9;]*m', '', text)
                text = ''.join(c for c in text if c.isprintable() or c in '\n\r\t')
                # Write directly to buffer to avoid print() encoding errors on Windows
                import sys
                sys.stdout.buffer.write(text.encode('utf-8', errors='replace'))
                sys.stdout.buffer.flush()
                await asyncio.sleep(0.1)

        # Write loop from stdin
        async def write_stream():
            loop = asyncio.get_event_loop()
            while True:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line: break
                writer.write(line.encode('utf-8'))
                await writer.drain()

        await asyncio.gather(read_stream(), write_stream())
    except Exception as e:
        print(f'ERROR: {e}')

asyncio.run(shell())
