import httpx
import asyncio

async def run():
    async with httpx.AsyncClient() as client:
        res = await client.get('http://127.0.0.1:8000/api/v2/runs/ccf852a5-4690-4357-b1d3-19e88fd89fa2')
        d = res.json()
        reviews = [r for r in d['records'] if r['deterministic_result']['status'] == 'review']
        multi = sum(1 for r in reviews if len(r['deterministic_result'].get('competing_candidates', [])) > 0)
        print(f'Total REVIEW: {len(reviews)}, With Competing: {multi}')

asyncio.run(run())
