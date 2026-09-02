import React, { useState } from 'react';
import type { BankRecord, WrappedReconciliationResult, OverrideRecord } from '../types';

interface DetailPanelProps {
    transaction: BankRecord;
    result: WrappedReconciliationResult;
    override: OverrideRecord | null;
    setOverride: (override: OverrideRecord) => void;
}

export const DetailPanel: React.FC<DetailPanelProps> = ({ transaction, result, override, setOverride }) => {
    const [showAudit, setShowAudit] = useState(false);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const res = result.deterministic_result;

    const currencySymbol = transaction.currency === 'USD' ? '$' : (transaction.currency === 'INR' ? '₹' : transaction.currency);
    const amount = transaction.amount.toFixed(2);
    
    // For formatting date, assume standard ISO
    const dateObj = new Date(transaction.transaction_date);
    const dateStr = isNaN(dateObj.getTime()) ? transaction.transaction_date : dateObj.toLocaleDateString();

    let mainSentence = "";
    if (res.status === 'unmatched' || !res.candidate) {
        mainSentence = `${currencySymbol}${amount} dated ${dateStr}, found no plausible matching candidate.`;
    } else {
        mainSentence = `${currencySymbol}${amount} dated ${dateStr}, matched against ${res.candidate.merchant_record.record_id} at ${res.candidate.confidence_score.toFixed(1)}% confidence.`;
    }

    const handleOverride = async (action: 'approve' | 'reject') => {
        setIsSubmitting(true);
        setErrorMsg(null);
        try {
            const payload = {
                transaction_id: transaction.record_id,
                candidate_id: res.candidate ? res.candidate.merchant_record.record_id : null
            };
            const response = await fetch(`http://127.0.0.1:8000/api/v1/overrides/${action}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || `HTTP Error ${response.status}`);
            }
            const data: OverrideRecord = await response.json();
            setOverride(data);
        } catch (e: any) {
            setErrorMsg(e.message || 'Error executing override');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <td colSpan={4} style={{ padding: 0 }}>
            <div style={{
                borderLeft: '3px solid var(--primary-accent)',
                paddingLeft: '1.25rem',
                paddingTop: '1rem',
                paddingBottom: '1.5rem',
                marginBottom: '1rem',
                marginLeft: '10px'
            }}>
                <div style={{ fontSize: '12px', color: 'var(--muted-gray)', marginBottom: '8px' }}>
                    {transaction.record_id}, under {res.status}
                </div>
                
                <div className="serif" style={{ fontSize: '18px', color: 'black', marginBottom: '16px' }}>
                    {mainSentence}
                </div>

                <div style={{ marginBottom: '24px' }}>
                    {res.audit_trail.map((line, idx) => {
                        const isMuted = line.toLowerCase().includes("routed to review") || 
                                        line.toLowerCase().includes("safety gate failed") ||
                                        line.toLowerCase().includes("< 70") ||
                                        line.toLowerCase().includes("routed to unmatched");
                        return (
                            <div key={idx} style={{ 
                                fontSize: '13px', 
                                lineHeight: 1.9,
                                color: isMuted ? 'var(--muted-gray)' : 'var(--body-ink)'
                            }}>
                                {line}
                            </div>
                        );
                    })}
                </div>
                
                {errorMsg && (
                    <div style={{ color: '#c62828', fontSize: '12px', marginBottom: '12px' }}>
                        {errorMsg}
                    </div>
                )}

                <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                    {override ? (
                        <span style={{ fontSize: '12px', color: 'var(--muted-gray)' }}>
                            ✓ Manually {override.action}d on {new Date(override.timestamp).toLocaleString()}
                        </span>
                    ) : (
                        <React.Fragment>
                            {res.candidate && (
                                <React.Fragment>
                                    <button 
                                        className="action-link" 
                                        style={{ color: 'var(--primary-accent)', textDecorationColor: 'var(--primary-accent)' }}
                                        onClick={(e) => { e.stopPropagation(); handleOverride('approve'); }}
                                        disabled={isSubmitting}
                                    >
                                        Approve match
                                    </button>
                                    <button 
                                        className="action-link" 
                                        style={{ color: 'black', textDecorationColor: 'black' }}
                                        onClick={(e) => { e.stopPropagation(); handleOverride('reject'); }}
                                        disabled={isSubmitting}
                                    >
                                        Reject
                                    </button>
                                </React.Fragment>
                            )}
                        </React.Fragment>
                    )}
                    
                    <button 
                        className="action-link" 
                        style={{ color: 'var(--muted-gray)', textDecorationColor: 'var(--muted-gray)' }}
                        onClick={(e) => {
                            e.stopPropagation();
                            setShowAudit(!showAudit);
                        }}
                    >
                        {showAudit ? "Hide audit trail" : "View audit trail"}
                    </button>
                </div>

                {showAudit && (
                    <div style={{ marginTop: '16px', padding: '12px', backgroundColor: 'var(--selected-row-tint)', fontSize: '12px', color: 'var(--muted-gray)' }}>
                        <strong>Raw Audit Trail:</strong>
                        <pre style={{ margin: 0, marginTop: '8px', whiteSpace: 'pre-wrap', fontFamily: 'var(--font-sans)' }}>
                            {JSON.stringify(res.audit_trail, null, 2)}
                        </pre>
                    </div>
                )}
            </div>
        </td>
    );
};
