import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        res = await client.get('http://127.0.0.1:8000/api/v2/runs/3b4dcb87-54c3-4635-b18b-0e3ee76ec5eb', timeout=10.0)
        data = res.json()
        records = data['records']
        auto = sum(1 for r in records if r['deterministic_result']['status'] == 'auto')
        review = sum(1 for r in records if r['deterministic_result']['status'] == 'review')
        unmatched = sum(1 for r in records if r['deterministic_result']['status'] == 'unmatched')
        print(f"TOTAL={len(records)} AUTO={auto} REVIEW={review} UNMATCHED={unmatched}")

asyncio.run(main())
