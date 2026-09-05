import httpx
import asyncio

async def run():
    async with httpx.AsyncClient() as client:
        res = await client.get('http://127.0.0.1:8000/api/v2/runs/ccf852a5-4690-4357-b1d3-19e88fd89fa2')
        data = res.json()
        records = data['records']
        r = [rec for rec in records if rec['deterministic_result']['status'] == 'review'][0]
        print(f"Transaction: {r['transaction_id']}")
        print(f"Competing length: {len(r['deterministic_result'].get('competing_candidates', []))}")

asyncio.run(run())
