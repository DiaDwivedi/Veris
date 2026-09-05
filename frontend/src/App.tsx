import { useState } from 'react';
import { ReconciliationDashboard } from './components/ReconciliationDashboard';
import type { BatchReconcileRequest, RunDetailResponse } from './types';
import devTxnsRaw from '../../data/dev_transactions.csv?raw';
import devOrdersRaw from '../../data/dev_orders.csv?raw';

function parseCSV(csvText: string): any[] {
    const lines = csvText.trim().split('\n');
    const headers = lines[0].split(',');
    const results = [];
    for (let i = 1; i < lines.length; i++) {
        const row = lines[i].split(',');
        if (row.length === headers.length) {
            const obj: any = {};
            for (let j = 0; j < headers.length; j++) {
                obj[headers[j].trim()] = row[j].trim();
            }
            results.push(obj);
        }
    }
    return results;
}

function buildPayloadFromCSV(txnsCsv: string, ordersCsv: string): BatchReconcileRequest {
    const txns = parseCSV(txnsCsv);
    const orders = parseCSV(ordersCsv);
    
    return {
        transactions: txns.map(t => ({
            record_id: t.id,
            amount: parseFloat(t.amount),
            currency: "USD",
            transaction_date: `${t.date}T00:00:00Z`,
            description: t.description,
            customer_id: t.customer_id || undefined,
            reference_id: t.reference || undefined,
            source: "bank"
        })),
        orders: orders.map(o => ({
            record_id: o.id,
            amount: parseFloat(o.amount),
            currency: "USD",
            transaction_date: `${o.date}T00:00:00Z`,
            description: o.description,
            customer_id: o.customer_id || undefined,
            reference_id: o.reference || undefined,
            source: "merchant"
        }))
    };
}

function App() {
    const [jsonInput, setJsonInput] = useState('');
    const [runDetail, setRunDetail] = useState<RunDetailResponse | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showAdvanced, setShowAdvanced] = useState(false);

    const handleLoadDevDataset = async () => {
        setIsLoading(true);
        setError(null);
        setRunDetail(null);
        
        try {
            const payload = buildPayloadFromCSV(devTxnsRaw, devOrdersRaw);
            await submitRun(payload);
        } catch (err: any) {
            setError(err.message || 'Error loading dev dataset');
            setIsLoading(false);
        }
    };

    const handleRunCustom = async () => {
        setIsLoading(true);
        setError(null);
        setRunDetail(null);
        try {
            const payload = JSON.parse(jsonInput) as BatchReconcileRequest;
            await submitRun(payload);
        } catch (err: any) {
            setError(err.message || 'Invalid JSON');
            setIsLoading(false);
        }
    };

    const submitRun = async (payload: BatchReconcileRequest) => {
        try {
            if (!payload.transactions || !Array.isArray(payload.transactions)) {
                throw new Error("Invalid payload: missing 'transactions' array.");
            }

            const createResponse = await fetch('http://127.0.0.1:8000/api/v2/runs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!createResponse.ok) {
                const errData = await createResponse.json();
                throw new Error(`API Error ${createResponse.status}: ${JSON.stringify(errData)}`);
            }

            const createData = await createResponse.json();
            const runId = createData.run_id;

            const fetchResponse = await fetch(`http://127.0.0.1:8000/api/v2/runs/${runId}`);
            if (!fetchResponse.ok) {
                const errData = await fetchResponse.json();
                throw new Error(`API Error ${fetchResponse.status}: ${JSON.stringify(errData)}`);
            }

            const detailData = await fetchResponse.json();
            setRunDetail(detailData);
        } catch (err: any) {
            setError(err.message || 'An unknown error occurred');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div>
            {error && (
                <div style={{ backgroundColor: 'var(--error-bg)', color: 'var(--error)', padding: '1rem', textAlign: 'center', fontSize: '14px' }}>
                    {error}
                </div>
            )}
            
            {!runDetail && (
                <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
                    <div style={{ width: '100%', maxWidth: '500px', display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '1rem', background: 'var(--surface)', border: '1px solid var(--border-subtle)', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}>
                        
                        <div style={{ textAlign: 'center', marginBottom: '0.5rem' }}>
                            <h2 style={{ fontSize: '24px', marginBottom: '8px', color: 'var(--text-primary)' }}>AI Finance Controller</h2>
                            <p style={{ color: 'var(--text-muted)', fontSize: '14px', margin: 0 }}>
                                Deterministic transaction-to-order reconciliation with a full audit trail.
                            </p>
                        </div>
                        
                        <div>
                            <button 
                                onClick={handleLoadDevDataset}
                                disabled={isLoading}
                                style={{ 
                                    padding: '12px 24px', 
                                    backgroundColor: 'var(--auto)', 
                                    color: '#fff', 
                                    border: 'none', 
                                    borderRadius: '4px',
                                    cursor: isLoading ? 'not-allowed' : 'pointer',
                                    width: '100%',
                                    fontWeight: 'bold',
                                    fontSize: '15px'
                                }}
                            >
                                {isLoading ? 'Running...' : 'Load Dev Dataset'}
                            </button>
                            <p style={{ textAlign: 'center', color: 'var(--text-faint)', fontSize: '12px', marginTop: '12px', marginBottom: 0 }}>
                                {parseCSV(devTxnsRaw).length} transactions, {parseCSV(devOrdersRaw).length} orders (dev split)
                            </p>
                        </div>

                        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
                            <button 
                                onClick={() => setShowAdvanced(!showAdvanced)}
                                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '12px', padding: 0 }}
                            >
                            {showAdvanced ? '▼ Hide Advanced' : '▶ Show Advanced (Raw JSON)'}
                        </button>
                        
                        {showAdvanced && (
                            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                <textarea 
                                    value={jsonInput}
                                    onChange={(e) => setJsonInput(e.target.value)}
                                    style={{ width: '100%', height: '200px', fontFamily: 'monospace', padding: '0.5rem', border: '1px solid var(--border-subtle)', background: 'var(--surface-deep)', color: 'var(--text)' }}
                                    placeholder="Paste JSON here..."
                                />
                                <button 
                                    onClick={handleRunCustom}
                                    disabled={isLoading || !jsonInput.trim()}
                                    style={{ padding: '8px 16px', background: 'var(--surface-deep)', color: 'var(--text)', border: '1px solid var(--border)', cursor: 'pointer' }}
                                >
                                    Run Custom JSON
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
            )}

            {runDetail && (
                <ReconciliationDashboard 
                    runDetail={runDetail} 
                    isLoading={isLoading} 
                />
            )}
        </div>
    );
}

export default App;
