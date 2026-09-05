import { useState, useRef } from 'react';
import { ReconciliationDashboard } from './components/ReconciliationDashboard';
import { EvaluationScreen } from './components/EvaluationScreen';
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

function buildPayloadFromParsed(txns: any[], orders: any[]): BatchReconcileRequest {
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
    const [showEval, setShowEval] = useState(false);

    // Upload states
    const [txnsFile, setTxnsFile] = useState<File | null>(null);
    const [ordersFile, setOrdersFile] = useState<File | null>(null);
    const [txnsParsed, setTxnsParsed] = useState<any[] | null>(null);
    const [ordersParsed, setOrdersParsed] = useState<any[] | null>(null);
    const [txnsError, setTxnsError] = useState<string | null>(null);
    const [ordersError, setOrdersError] = useState<string | null>(null);

    const txnsInputRef = useRef<HTMLInputElement>(null);
    const ordersInputRef = useRef<HTMLInputElement>(null);

    const handleLoadDevDataset = async () => {
        setIsLoading(true);
        setError(null);
        setRunDetail(null);
        
        try {
            const txns = parseCSV(devTxnsRaw);
            const orders = parseCSV(devOrdersRaw);
            const payload = buildPayloadFromParsed(txns, orders);
            await submitRun(payload);
        } catch (err: any) {
            setError(err.message || 'Error loading dev dataset');
            setIsLoading(false);
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, type: 'txns' | 'orders') => {
        const file = e.target.files?.[0];
        if (!file) return;
        
        if (type === 'txns') {
            setTxnsFile(file);
            setTxnsError(null);
            setTxnsParsed(null);
        } else {
            setOrdersFile(file);
            setOrdersError(null);
            setOrdersParsed(null);
        }

        try {
            const text = await file.text();
            if (!text.trim()) throw new Error("File is empty");
            const parsed = parseCSV(text);
            if (parsed.length === 0) throw new Error("No data rows found");
            
            const required = ['id', 'amount', 'date', 'customer_id', 'reference', 'description'];
            const headers = Object.keys(parsed[0]);
            for (const req of required) {
                if (!headers.includes(req)) {
                    throw new Error(`Missing required column: ${req}`);
                }
            }
            
            if (type === 'txns') {
                setTxnsParsed(parsed);
            } else {
                setOrdersParsed(parsed);
            }
        } catch (err: any) {
            if (type === 'txns') setTxnsError(`${file.name}: ${err.message}`);
            else setOrdersError(`${file.name}: ${err.message}`);
        }
    };

    const handleRunCustomUpload = async () => {
        if (!txnsParsed || !ordersParsed) return;
        setIsLoading(true);
        setError(null);
        setRunDetail(null);
        try {
            const payload = buildPayloadFromParsed(txnsParsed, ordersParsed);
            await submitRun(payload);
        } catch (err: any) {
            setError(err.message || 'Error running uploaded dataset');
            setIsLoading(false);
        }
    };

    const handleRunCustomJson = async () => {
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

            const createResponse = await fetch('/api/v2/runs', {
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

            const fetchResponse = await fetch(`/api/v2/runs/${runId}`);
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

    const devTxnsCount = parseCSV(devTxnsRaw).length;
    const devOrdersCount = parseCSV(devOrdersRaw).length;
    const canRunUploads = txnsParsed !== null && ordersParsed !== null;

    return (
        <div>
            <style>{`
                .narrow-notice {
                    display: none;
                    color: var(--text-muted);
                    font-size: 12px;
                    text-align: center;
                    margin-top: 1rem;
                }
                @media (max-width: 799px) {
                    .narrow-notice {
                        display: block;
                    }
                }
            `}</style>
            
            {error && (
                <div style={{ backgroundColor: 'var(--error-bg)', color: 'var(--error)', padding: '1rem', textAlign: 'center', fontSize: '14px' }}>
                    {error}
                </div>
            )}
            
            {showEval ? (
                <div>
                    <button onClick={() => setShowEval(false)} style={{ margin: '1rem 2rem', padding: '8px 16px', background: 'var(--surface-deep)', color: 'var(--text)', border: '1px solid var(--border)', cursor: 'pointer', borderRadius: '4px' }}>
                        &larr; Back
                    </button>
                    <EvaluationScreen />
                </div>
            ) : runDetail ? (
                <ReconciliationDashboard 
                    runDetail={runDetail} 
                    isLoading={isLoading} 
                    onViewEval={() => setShowEval(true)}
                />
            ) : (
                <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
                    
                    {/* Header */}
                    <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                        <div style={{ 
                            display: 'inline-flex', 
                            alignItems: 'center', 
                            justifyContent: 'center', 
                            width: '48px', 
                            height: '48px', 
                            background: 'var(--review-bg)', 
                            border: '1px solid var(--review-dark)', 
                            borderRadius: '8px', 
                            marginBottom: '1rem' 
                        }}>
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--review)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>
                            </svg>
                        </div>
                        <h1 style={{ fontSize: '25px', fontWeight: '500', letterSpacing: '0.14em', marginBottom: '8px', color: 'var(--text-primary)' }}>VERIS</h1>
                        <p style={{ color: 'var(--review)', fontSize: '13px', margin: 0 }}>
                            Built to decide. Designed to prove.
                        </p>
                    </div>
                    
                    {/* Card */}
                    <div style={{ width: '100%', maxWidth: '440px', display: 'flex', flexDirection: 'column', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px' }}>
                        
                        <div style={{ padding: '1.5rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', fontSize: '12px', marginBottom: '1.5rem' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <span style={{ color: 'var(--auto)' }}>●</span> <span style={{ color: 'var(--text)' }}>Auto</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <span style={{ color: 'var(--review)' }}>●</span> <span style={{ color: 'var(--text)' }}>Review</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <span style={{ color: '#4D4D4C' }}>●</span> <span style={{ color: 'var(--text)' }}>Unmatched</span>
                                </div>
                            </div>
                            
                            <p style={{ textAlign: 'center', color: 'var(--text-faint)', fontSize: '12px', margin: '0 0 2rem 0', lineHeight: '1.5' }}>
                                Every transaction gets one outcome<br />
                                and the evidence behind it.
                            </p>

                            {/* Dev Dataset */}
                            <button 
                                onClick={handleLoadDevDataset}
                                disabled={isLoading}
                                style={{ 
                                    padding: '12px 16px', 
                                    background: 'var(--surface-deep)', 
                                    color: 'var(--text-primary)', 
                                    border: '1px solid var(--unmatched-border)', 
                                    borderRadius: '6px',
                                    cursor: isLoading ? 'not-allowed' : 'pointer',
                                    width: '100%',
                                    fontWeight: '500',
                                    fontSize: '15px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '8px'
                                }}
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--auto)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polygon points="5 3 19 12 5 21 5 3"/>
                                </svg>
                                {isLoading ? 'Running...' : 'Load dev dataset'}
                            </button>
                            <p style={{ textAlign: 'center', color: 'var(--text-faint)', fontSize: '12px', marginTop: '12px', marginBottom: '1.5rem' }}>
                                {devTxnsCount} transactions <span style={{ color: 'var(--border)' }}>·</span> {devOrdersCount} orders <span style={{ color: 'var(--border)' }}>·</span> dev split
                            </p>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: '1.5rem 0' }}>
                                <div style={{ height: '1px', background: 'var(--border-subtle)', flex: 1 }}></div>
                                <span style={{ color: 'var(--text-faint)', fontSize: '12px' }}>OR</span>
                                <div style={{ height: '1px', background: 'var(--border-subtle)', flex: 1 }}></div>
                            </div>

                            {/* Custom Data Upload */}
                            <p style={{ color: 'var(--text-primary)', fontSize: '14px', marginBottom: '12px', textAlign: 'left' }}>
                                Use your own data
                            </p>
                            
                            <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
                                <input 
                                    type="file" 
                                    accept=".csv" 
                                    ref={txnsInputRef} 
                                    onChange={(e) => handleFileUpload(e, 'txns')} 
                                    style={{ display: 'none' }} 
                                />
                                <button 
                                    onClick={() => txnsInputRef.current?.click()}
                                    style={{ 
                                        flex: 1, 
                                        padding: '10px', 
                                        background: 'var(--surface-deep)', 
                                        border: '1px dashed var(--border)', 
                                        borderRadius: '6px', 
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '8px',
                                        color: 'var(--text)'
                                    }}
                                >
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--review)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                                    </svg>
                                    <span style={{ fontSize: '13px' }}>Transactions</span>
                                </button>

                                <input 
                                    type="file" 
                                    accept=".csv" 
                                    ref={ordersInputRef} 
                                    onChange={(e) => handleFileUpload(e, 'orders')} 
                                    style={{ display: 'none' }} 
                                />
                                <button 
                                    onClick={() => ordersInputRef.current?.click()}
                                    style={{ 
                                        flex: 1, 
                                        padding: '10px', 
                                        background: 'var(--surface-deep)', 
                                        border: '1px dashed var(--border)', 
                                        borderRadius: '6px', 
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '8px',
                                        color: 'var(--text)'
                                    }}
                                >
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--review)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                                    </svg>
                                    <span style={{ fontSize: '13px' }}>Orders</span>
                                </button>
                            </div>

                            {/* File Status & Errors */}
                            {(txnsFile || ordersFile || txnsError || ordersError) && (
                                <div style={{ fontSize: '12px', marginBottom: '1rem' }}>
                                    {txnsError && <div style={{ color: '#E06C75', marginBottom: '4px' }}>{txnsError}</div>}
                                    {!txnsError && txnsFile && (
                                        <div style={{ color: 'var(--text-faint)', marginBottom: '4px' }}>
                                            {txnsFile.name} <span style={{ color: 'var(--border)' }}>·</span> {txnsParsed?.length ?? 0} rows
                                        </div>
                                    )}
                                    
                                    {ordersError && <div style={{ color: '#E06C75', marginBottom: '4px' }}>{ordersError}</div>}
                                    {!ordersError && ordersFile && (
                                        <div style={{ color: 'var(--text-faint)', marginBottom: '4px' }}>
                                            {ordersFile.name} <span style={{ color: 'var(--border)' }}>·</span> {ordersParsed?.length ?? 0} rows
                                        </div>
                                    )}
                                </div>
                            )}

                            <button 
                                onClick={handleRunCustomUpload}
                                disabled={!canRunUploads || isLoading}
                                style={{ 
                                    padding: '12px 16px', 
                                    background: 'var(--surface-deep)', 
                                    color: canRunUploads ? 'var(--text-primary)' : 'var(--unmatched-border)', 
                                    border: '1px solid var(--unmatched-border)', 
                                    borderRadius: '6px',
                                    cursor: (!canRunUploads || isLoading) ? 'not-allowed' : 'pointer',
                                    width: '100%',
                                    fontWeight: '500',
                                    fontSize: '15px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '8px'
                                }}
                            >
                                {canRunUploads && (
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--auto)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <polygon points="5 3 19 12 5 21 5 3"/>
                                    </svg>
                                )}
                                {isLoading ? 'Running...' : 'Run reconciliation'}
                            </button>
                        </div>
                    </div>

                    {/* Footer Advanced Options */}
                    <div style={{ width: '100%', maxWidth: '440px', marginTop: '1.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <button 
                                onClick={() => setShowAdvanced(!showAdvanced)}
                                style={{ background: 'none', border: 'none', color: 'var(--text-faint)', cursor: 'pointer', fontSize: '12px', padding: 0, display: 'flex', alignItems: 'center', gap: '4px' }}
                            >
                                {showAdvanced ? '▾' : '▸'} Advanced
                            </button>
                            <span style={{ color: 'var(--text-faint)', fontSize: '12px', fontFamily: 'monospace' }}>
                                config frozen
                            </span>
                        </div>
                        
                        {showAdvanced && (
                            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <button 
                                        onClick={() => setShowEval(true)}
                                        style={{ background: 'none', border: 'none', color: 'var(--text-faint)', textDecoration: 'underline', cursor: 'pointer', fontSize: '12px', padding: 0 }}
                                    >
                                        View Evaluation Report
                                    </button>
                                </div>
                                <textarea 
                                    value={jsonInput}
                                    onChange={(e) => setJsonInput(e.target.value)}
                                    style={{ width: '100%', height: '200px', fontFamily: 'monospace', padding: '0.5rem', border: '1px solid var(--border-subtle)', background: 'var(--surface-deep)', color: 'var(--text)', borderRadius: '6px' }}
                                    placeholder="Paste JSON payload here..."
                                />
                                <button 
                                    onClick={handleRunCustomJson}
                                    disabled={isLoading || !jsonInput.trim()}
                                    style={{ padding: '8px 16px', background: 'var(--surface-deep)', color: 'var(--text)', border: '1px solid var(--border)', cursor: 'pointer', borderRadius: '4px', fontSize: '13px' }}
                                >
                                    Run Custom JSON
                                </button>
                            </div>
                        )}
                    </div>
                    
                    <div className="narrow-notice">
                        Best viewed on desktop. Some screens are not optimised for narrow displays.
                    </div>
                </div>
            )}
        </div>
    );
}

export default App;
