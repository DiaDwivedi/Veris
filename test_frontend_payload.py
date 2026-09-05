import json
import httpx
import asyncio

def parse_csv_like_frontend(csv_text):
    lines = csv_text.strip().split('\n')
    headers = lines[0].split(',')
    results = []
    for line in lines[1:]:
        row = line.split(',')
        if len(row) == len(headers):
            obj = {}
            for j in range(len(headers)):
                obj[headers[j].strip()] = row[j].strip()
            results.append(obj)
    return results

def build_payload(txns_csv, orders_csv):
    txns = parse_csv_like_frontend(txns_csv)
    orders = parse_csv_like_frontend(orders_csv)
    
    payload_txns = []
    for t in txns:
        payload_txns.append({
            "record_id": t["id"],
            "amount": float(t["amount"]),
            "currency": "USD",
            "transaction_date": f"{t['date']}T00:00:00Z",
            "description": t["description"],
            "customer_id": t["customer_id"] if t["customer_id"] else None,
            "reference_id": t["reference"] if t["reference"] else None,
            "source": "bank"
        })
        
    payload_orders = []
    for o in orders:
        payload_orders.append({
            "record_id": o["id"],
            "amount": float(o["amount"]),
            "currency": "USD",
            "transaction_date": f"{o['date']}T00:00:00Z",
            "description": o["description"],
            "customer_id": o["customer_id"] if o["customer_id"] else None,
            "reference_id": o["reference"] if o["reference"] else None,
            "source": "merchant"
        })
        
    return {"transactions": payload_txns, "orders": payload_orders}

async def main():
    with open('data/dev_transactions.csv', 'r', encoding='utf-8') as f:
        txns_csv = f.read()
    with open('data/dev_orders.csv', 'r', encoding='utf-8') as f:
        orders_csv = f.read()
        
    payload = build_payload(txns_csv, orders_csv)
    
    async with httpx.AsyncClient() as client:
        res = await client.post('http://127.0.0.1:8000/api/v2/runs', json=payload)
        run_id = res.json()["run_id"]
        
        res = await client.get(f'http://127.0.0.1:8000/api/v2/runs/{run_id}')
        data = res.json()
        reviews = [r for r in data['records'] if r['deterministic_result']['status'] == 'review']
        multi = sum(1 for r in reviews if len(r['deterministic_result'].get('competing_candidates', [])) > 0)
        print(f"Total REVIEW from frontend payload: {len(reviews)}, With Competing: {multi}")

if __name__ == '__main__':
    asyncio.run(main())
