import asyncio
from app.local_generator import LocalGenerator
from app.generator_client import GenerationRequest

async def main():
    g = LocalGenerator()
    conf, meta = await g.generate(GenerationRequest(mode='legacy'))
    print(conf)

if __name__ == '__main__':
    asyncio.run(main())
