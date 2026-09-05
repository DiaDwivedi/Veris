import httpx
import asyncio

async def run():
    async with httpx.AsyncClient() as client:
        res = await client.get('http://127.0.0.1:8000/api/v2/runs/ccf852a5-4690-4357-b1d3-19e88fd89fa2')
        d = res.json()
        
        near_ties = []
        fired_near_tie_rule = []
        
        for r in d['records']:
            det = r['deterministic_result']
            if det['routing_reason'] == 'near_tie':
                fired_near_tie_rule.append(r['transaction_id'])
                
            comp = det.get('competing_candidates', [])
            if len(comp) > 0:
                top_cand = det['candidate']
                if not top_cand:
                    continue
                
                cands = [top_cand] + comp
                cands.sort(key=lambda x: x['confidence_score'], reverse=True)
                
                if len(cands) >= 2:
                    gap = cands[0]['confidence_score'] - cands[1]['confidence_score']
                    
                    cand_list = [(c['merchant_record']['record_id'], c['confidence_score']) for c in cands]
                    
                    near_ties.append({
                        'transaction_id': r['transaction_id'],
                        'final_score': top_cand['confidence_score'],
                        'gap': gap,
                        'cands': cand_list
                    })
                    
        near_ties.sort(key=lambda x: x['gap'])
        
        print("TOP 5 SMALLEST GAPS:")
        for t in near_ties[:5]:
            print(f"TXN: {t['transaction_id']} | Final Score: {t['final_score']} | Gap: {t['gap']}")
            print(f"  Candidates:")
            for c_id, c_score in t['cands']:
                print(f"    {c_id}: {c_score}")
            print()
            
        print("Near-tie rule fired on:", fired_near_tie_rule)

asyncio.run(run())
