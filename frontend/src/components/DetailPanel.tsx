import React, { useState, useEffect } from 'react';
import type { RecordDetail, OverrideRecordV2 } from '../types';

interface DetailPanelProps {
    record: RecordDetail;
    runId: string;
    onClose: () => void;
}

export const DetailPanel: React.FC<DetailPanelProps> = ({ record, runId, onClose }) => {
    const res = record.deterministic_result;
    const history = record.override_history;
    
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [localHistory, setLocalHistory] = useState<OverrideRecordV2[]>(history);
    const [selectedCandidate, setSelectedCandidate] = useState<string | null>(res.candidate ? res.candidate.merchant_record.record_id : null);
    
    useEffect(() => {
        setLocalHistory(record.override_history);
        setSelectedCandidate(res.candidate ? res.candidate.merchant_record.record_id : null);
    }, [record, res.candidate]);

    const handleOverride = async (action: 'approve' | 'reject', candId: string | null) => {
        setIsSubmitting(true);
        setErrorMsg(null);
        try {
            const payload = {
                action: action,
                candidate_id: action === 'approve' ? candId : null
            };
            const response = await fetch(`/api/v2/runs/${runId}/records/${record.transaction_id}/override`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || `HTTP Error ${response.status}`);
            }
            const data: OverrideRecordV2 = await response.json();
            setLocalHistory([...localHistory, data]);
        } catch (e: any) {
            setErrorMsg(e.message || 'Error executing override');
        } finally {
            setIsSubmitting(false);
        }
    };

    const statusBg = res.status === 'auto' ? 'var(--auto-bg)' : res.status === 'review' ? 'var(--review-bg)' : 'var(--unmatched-bg)';
    const statusColor = res.status === 'auto' ? 'var(--auto)' : res.status === 'review' ? 'var(--review)' : 'var(--unmatched-text)';

    // Candidate universe deduplication
    const candidateSet = new Map<string, number>();
    if (res.candidate) {
        candidateSet.set(res.candidate.merchant_record.record_id, res.candidate.confidence_score);
    }
    if (res.competing_candidates) {
        for (const c of res.competing_candidates) {
            candidateSet.set(c.merchant_record.record_id, c.confidence_score);
        }
    }
    const selectableCandidates = Array.from(candidateSet.entries()).map(([id, score]) => ({ id, score }));
    
    const isBelowFloor = res.status === 'unmatched';
    const hasSignals = res.signal_scores && Object.keys(res.signal_scores).length > 0;

    return (
        <div style={{
            background: 'var(--surface)',
            color: 'var(--text)',
            height: '100%',
            overflowY: 'auto'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <button onClick={onClose} style={{ background: 'var(--surface-deep)', border: '1px solid var(--border)', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '14px', padding: '4px 12px', borderRadius: '4px' }}>← Back to Dashboard</button>
                    <div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>TXN ID</div>
                        <div style={{ fontSize: '16px', color: 'var(--text-primary)', fontWeight: 'bold' }}>{record.transaction_id}</div>
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '2rem' }}>
                
                {/* Left Column: Original Deterministic Result */}
                <div>
                    <h3 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px', marginBottom: '16px', fontWeight: 'bold' }}>
                        Original Deterministic Evaluation
                    </h3>
                    
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem', background: 'var(--surface-deep)', padding: '1rem', border: '1px solid var(--border-subtle)', borderRadius: '4px' }}>
                        <div>
                            <span className="uppercase" style={{
                                color: statusColor,
                                backgroundColor: statusBg,
                                padding: '4px 12px',
                                borderRadius: '12px',
                                fontSize: '10px',
                                fontWeight: 'bold',
                                display: 'inline-block',
                                marginBottom: '12px'
                            }}>
                                {res.status}
                            </span>
                            <div style={{ fontSize: '16px', color: 'var(--text-primary)', marginBottom: '8px', lineHeight: 1.4, fontWeight: 'bold' }}>
                                {res.why}
                            </div>
                            <div style={{ fontSize: '13px', color: 'var(--text)', lineHeight: 1.5 }}>
                                {res.explanation}
                            </div>
                        </div>
                        <div style={{ textAlign: 'right', marginLeft: '1rem' }}>
                            <div style={{ fontSize: '32px', fontWeight: 'bold', color: 'var(--text-primary)', lineHeight: 1 }}>
                                {res.candidate ? `${Math.round(res.candidate.confidence_score)}` : '—'}
                            </div>
                            {res.candidate && <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Score</div>}
                        </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                        {/* Signals */}
                        <div>
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px', fontWeight: 'bold' }}>Signal Breakdown</div>
                            {hasSignals ? (
                                Object.entries(res.signal_scores || {}).map(([key, signal]) => {
                                    const max = signal.max > 0 ? signal.max : 1;
                                    const pct = Math.min(100, Math.max(0, (signal.earned / max) * 100));
                                    return (
                                        <div key={key} style={{ marginBottom: '12px' }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '4px' }}>
                                                <span style={{ color: 'var(--text)' }}>{key.replace('WEIGHT_', '')}</span>
                                                <span style={{ color: 'var(--text-primary)' }}>{signal.earned} / {signal.max}</span>
                                            </div>
                                            <div style={{ width: '100%', height: '4px', background: 'var(--surface-inset)', borderRadius: '2px' }}>
                                                <div style={{ width: `${pct}%`, height: '100%', background: 'var(--auto)', borderRadius: '2px' }} />
                                            </div>
                                            {signal.outcome && (
                                                <div style={{ fontSize: '10px', color: 'var(--text-faint)', marginTop: '4px' }}>{signal.outcome}</div>
                                            )}
                                        </div>
                                    );
                                })
                            ) : (
                                <div style={{ fontSize: '12px', color: 'var(--text-faint)', fontStyle: 'italic', padding: '1rem', background: 'var(--surface-inset)', borderRadius: '4px' }}>
                                    No candidate qualified for a signal breakdown.
                                </div>
                            )}
                        </div>

                        {/* Candidates */}
                        <div>
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px', fontWeight: 'bold' }}>Candidates Considered</div>
                            {selectableCandidates.length > 0 ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                    {selectableCandidates.map((c, i) => (
                                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--surface-deep)', border: '1px solid var(--border-subtle)', borderRadius: '4px', fontSize: '12px' }}>
                                            <span style={{ color: 'var(--text-primary)', fontFamily: 'monospace' }}>{c.id}</span>
                                            <span style={{ color: 'var(--text-muted)' }}>{Math.round(c.score)}/100</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div style={{ fontSize: '12px', color: 'var(--text-faint)', fontStyle: 'italic', padding: '1rem', background: 'var(--surface-inset)', borderRadius: '4px' }}>No competing candidates found.</div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right Column: Actions and History */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                    
                    {/* Actions */}
                    <div>
                        <h3 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px', marginBottom: '12px', fontWeight: 'bold' }}>
                            {isBelowFloor ? 'MANUAL OVERRIDE' : 'Take Action'}
                        </h3>
                        
                        {errorMsg && (
                            <div style={{ color: 'var(--error)', background: 'var(--error-bg)', padding: '8px', fontSize: '12px', marginBottom: '12px', borderRadius: '4px' }}>
                                {errorMsg}
                            </div>
                        )}

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {isBelowFloor && (
                                <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                                    The engine did not approve any candidate. A reviewer may select one after manual review.
                                </div>
                            )}

                            {selectableCandidates.length > 0 && (
                                <select 
                                    value={selectedCandidate || ''} 
                                    onChange={(e) => setSelectedCandidate(e.target.value)}
                                    style={{ padding: '8px', background: 'var(--surface-deep)', color: 'var(--text-primary)', border: '1px solid var(--border)', borderRadius: '4px', fontSize: '12px', width: '100%' }}
                                >
                                    <option value="" disabled>Select a candidate to approve</option>
                                    {selectableCandidates.map(c => (
                                        <option key={c.id} value={c.id}>
                                            {c.id} ({Math.round(c.score)}/100)
                                        </option>
                                    ))}
                                </select>
                            )}

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <button 
                                    onClick={() => handleOverride('approve', selectedCandidate)}
                                    disabled={isSubmitting || !selectedCandidate}
                                    style={{ padding: '10px', background: isBelowFloor ? 'var(--review-bg)' : 'var(--auto-bg)', color: isBelowFloor ? 'var(--review)' : 'var(--auto)', border: `1px solid ${isBelowFloor ? 'var(--review)' : 'var(--auto)'}`, cursor: isSubmitting || !selectedCandidate ? 'not-allowed' : 'pointer', borderRadius: '4px', fontWeight: 'bold', fontSize: '12px' }}
                                >
                                    {isBelowFloor ? 'Override and approve' : 'Approve Match'}
                                </button>
                                <button 
                                    onClick={() => handleOverride('reject', null)}
                                    disabled={isSubmitting}
                                    style={{ padding: '10px', background: 'var(--surface-deep)', color: 'var(--text-primary)', border: '1px solid var(--border)', cursor: isSubmitting ? 'not-allowed' : 'pointer', borderRadius: '4px', fontSize: '12px' }}
                                >
                                    Mark Unmatched
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* History */}
                    <div>
                        <h3 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px', marginBottom: '12px', fontWeight: 'bold' }}>
                            Reviewer Action History
                        </h3>
                        
                        {localHistory.length > 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {localHistory.map((ov, i) => (
                                    <div key={i} style={{ padding: '12px', borderLeft: `2px solid ${ov.action === 'approve' ? 'var(--auto)' : 'var(--text-primary)'}`, background: 'var(--surface-inset)', fontSize: '11px' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                            <strong className="uppercase" style={{ color: ov.action === 'approve' ? 'var(--auto)' : 'var(--text-primary)' }}>{ov.action}</strong>
                                            <span style={{ color: 'var(--text-faint)' }}>{new Date(ov.created_at).toLocaleString()}</span>
                                        </div>
                                        {ov.candidate_id && <div style={{ color: 'var(--text)' }}>Candidate: {ov.candidate_id}</div>}
                                        {ov.reviewer_note && <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '4px' }}>"{ov.reviewer_note}"</div>}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div style={{ fontSize: '12px', color: 'var(--text-faint)', fontStyle: 'italic' }}>No manual actions recorded.</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
