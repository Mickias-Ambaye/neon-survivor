"""Entry point for Pygbag web builds and local play."""
import asyncio
from game import Game

async def main():
    game = Game()
    await game.run()

asyncio.run(main())
