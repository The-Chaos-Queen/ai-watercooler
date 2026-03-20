
import asyncio
import re
import httpx
from pathlib import Path

MUD_HOST = "127.0.0.1"
MUD_PORT = 4000

class TourAgent:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.reader = None
        self.writer = None
        self.visited_rooms = set()

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(MUD_HOST, MUD_PORT)
        
    async def send(self, cmd):
        self.writer.write((cmd + "\n").encode())
        await self.writer.drain()

    async def read(self, timeout=1.5):
        chunks = []
        try:
            while True:
                data = await asyncio.wait_for(self.reader.read(4096), timeout=timeout)
                if not data: break
                text = data.decode("utf-8", errors="replace")
                chunks.append(text)
                await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            pass
        return "".join(chunks)

    def parse_room_name(self, text):
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line and "Exits:" not in line and "You see:" not in line and "Characters:" not in line and "[SYSTEM_DATA]" not in line and "---" not in line:
                # Basic heuristic for room name
                return line
        return "Unknown Room"

    def parse_exits(self, text):
        match = re.search(r"Exits: (.+)", text)
        if match:
            # Clean ANSI and IDs
            ex_str = re.sub(r'\(#\d+\)', '', match.group(1))
            return [e.strip() for e in ex_str.split(",")]
        return []

    async def run_tour(self):
        await self.connect()
        await self.read(2.0)
        await self.send(f"connect {self.username} {self.password}")
        await asyncio.sleep(2.0)
        await self.read()
        print("Login complete.")

        # Initial look
        await self.send("look")
        await asyncio.sleep(1.0)
        initial_view = await self.read()
        
        current_room = self.parse_room_name(initial_view)
        print(f"Starting at: {current_room}")

        # Queue of paths (list of exit names to reach a new room)
        # We'll do a simple BFS exploration
        to_explore = [[]] # Start at current location
        seen_rooms = {current_room}

        while to_explore:
            path = to_explore.pop(0)
            
            # Navigate to the room defined by path
            # (Reset to starting point or just continue from current?)
            # Reset is safer for a tour.
            await self.send("look")
            await asyncio.sleep(0.5)
            await self.read() # Flush
            
            # Start from 'Square' or 'Tavern' manually if needed?
            # Let's assume we can always get back or just BFS from current.
            
            # For simplicity, if path exists, traverse it
            for step in path:
                await self.send(step)
                await asyncio.sleep(1.0)
                await self.read()

            # Now we are in a (hopefully) new room
            await self.send("look")
            await asyncio.sleep(1.0)
            view = await self.read()
            room_name = self.parse_room_name(view)
            
            print(f"\n--- AT: {room_name} ---")
            # print(view) # Debug
            
            exits = self.parse_exits(view)
            print(f"Exits: {exits}")

            for ex in exits:
                # This is tricky without knowing where they lead
                # But we can try to explore them
                # In this tour, we'll just report them
                pass

        print("\nTOUR COMPLETE.")
        self.writer.close()

if __name__ == "__main__":
    agent = TourAgent("Antigravity", "agentpass")
    asyncio.run(agent.run_tour())
