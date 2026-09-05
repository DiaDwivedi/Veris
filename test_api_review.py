import httpx
import asyncio

async def run():
    async with httpx.AsyncClient() as client:
        res = await client.get('http://127.0.0.1:8000/api/v2/runs/ccf852a5-4690-4357-b1d3-19e88fd89fa2')
        d = res.json()
        reviews = [r for r in d['records'] if r['deterministic_result']['status'] == 'review']
        for r in reviews:
            det = r['deterministic_result']
            print(r['transaction_id'], det['candidate']['merchant_record']['record_id'], det['candidate']['confidence_score'])

asyncio.run(run())
