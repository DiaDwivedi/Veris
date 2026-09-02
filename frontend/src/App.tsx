import { useState } from 'react';
import { ReconciliationDashboard } from './components/ReconciliationDashboard';
import type { BankRecord, WrappedReconciliationResult, BatchReconcileRequest } from './types';

const DEV_FIXTURE: BatchReconcileRequest = {
    transactions: [
        {
            record_id: "TXN_1",
            amount: 100.0,
            currency: "USD",
            transaction_date: "2026-09-02T00:00:00Z",
            description: "Amazon Retail",
            source: "bank"
        },
        {
            record_id: "TXN_2",
            amount: 250.0,
            currency: "USD",
            transaction_date: "2026-09-02T12:00:00Z",
            description: "Unknown Merchant",
            source: "bank"
        }
    ],
    orders: [
        {
            record_id: "ORD_1",
            amount: 100.0,
            currency: "USD",
            transaction_date: "2026-09-02T00:00:00Z",
            description: "Amazon Retail",
            source: "merchant"
        }
    ]
};

function App() {
    const [jsonInput, setJsonInput] = useState('');
    const [transactions, setTransactions] = useState<BankRecord[]>([]);
    const [results, setResults] = useState<WrappedReconciliationResult[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleLoadFixture = () => {
        setJsonInput(JSON.stringify(DEV_FIXTURE, null, 2));
    };

    const handleRunReconciliation = async () => {
        setIsLoading(true);
        setError(null);
        setResults([]);
        setTransactions([]);

        try {
            const payload = JSON.parse(jsonInput) as BatchReconcileRequest;
            if (!payload.transactions || !Array.isArray(payload.transactions)) {
                throw new Error("Invalid payload: missing 'transactions' array.");
            }

            const response = await fetch('http://127.0.0.1:8000/api/v2/reconcile/batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(`API Error ${response.status}: ${JSON.stringify(errData)}`);
            }

            const data = await response.json();
            setTransactions(payload.transactions);
            setResults(data.results);
        } catch (err: any) {
            setError(err.message || 'An unknown error occurred');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div>
            {error && (
                <div style={{ backgroundColor: '#ffebee', color: '#c62828', padding: '1rem', textAlign: 'center', fontFamily: 'var(--font-sans)', fontSize: '14px' }}>
                    {error}
                </div>
            )}
            
            <div style={{ maxWidth: '1000px', margin: '2rem auto', display: 'flex', flexDirection: 'column', gap: '1rem', fontFamily: 'var(--font-sans)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2 style={{ fontSize: '18px' }}>Batch Input</h2>
                    <button onClick={handleLoadFixture} style={{ padding: '4px 8px', fontSize: '12px', cursor: 'pointer' }}>
                        Load Dev Fixture
                    </button>
                </div>
                
                <textarea 
                    value={jsonInput}
                    onChange={(e) => setJsonInput(e.target.value)}
                    style={{ width: '100%', height: '200px', fontFamily: 'monospace', padding: '0.5rem', border: '1px solid var(--table-hairlines)' }}
                    placeholder="Paste BatchReconcileRequest JSON here..."
                />
                
                <button 
                    onClick={handleRunReconciliation}
                    disabled={isLoading || !jsonInput.trim()}
                    style={{ 
                        padding: '8px 16px', 
                        backgroundColor: 'var(--body-ink)', 
                        color: 'white', 
                        border: 'none', 
                        cursor: isLoading || !jsonInput.trim() ? 'not-allowed' : 'pointer',
                        width: 'fit-content'
                    }}
                >
                    {isLoading ? 'Running...' : 'Run Batch Reconciliation'}
                </button>
            </div>

            <ReconciliationDashboard 
                transactions={transactions} 
                results={results} 
                isLoading={isLoading} 
            />
        </div>
    );
}

export default App;
