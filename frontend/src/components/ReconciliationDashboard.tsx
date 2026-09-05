import React, { useState } from 'react';
import type { RunDetailResponse } from '../types';
import { HeroPanel } from './HeroPanel';
import { RateStrip } from './RateStrip';
import { LedgerTable } from './LedgerTable';
import { DetailPanel } from './DetailPanel';

interface ReconciliationDashboardProps {
    runDetail: RunDetailResponse;
    isLoading: boolean;
    onViewEval?: () => void;
}

export const ReconciliationDashboard: React.FC<ReconciliationDashboardProps> = ({ runDetail, isLoading, onViewEval }) => {
    const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);
    const [filter, setFilter] = useState<'all' | 'auto' | 'review' | 'unmatched'>('all');

    const records = runDetail.records;
    
    let total = records.length;
    let autoCount = 0;
    let reviewCount = 0;
    let unmatchedCount = 0;

    if (!isLoading && total > 0) {
        records.forEach(rec => {
            const res = rec.deterministic_result;
            if (res.status === 'auto') autoCount++;
            else if (res.status === 'review') reviewCount++;
            else if (res.status === 'unmatched') unmatchedCount++;
        });
    }

    const filteredRecords = records.filter(rec => {
        if (filter === 'all') return true;
        return rec.deterministic_result.status === filter;
    });

    const selectedRecord = selectedRecordId 
        ? records.find(r => r.transaction_id === selectedRecordId) || null
        : null;

    if (selectedRecord) {
        return (
            <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
                <DetailPanel 
                    record={selectedRecord} 
                    runId={runDetail.run.run_id} 
                    onClose={() => setSelectedRecordId(null)} 
                />
            </div>
        );
    }

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--review)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>
                    </svg>
                    <h1 style={{ fontSize: '18px', fontWeight: '600', fontVariant: 'small-caps', letterSpacing: '0.05em', margin: 0, color: 'var(--text-primary)' }}>VERIS</h1>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '12px', color: 'var(--text-muted)' }}>
                    {onViewEval && (
                        <button 
                            onClick={onViewEval} 
                            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', textDecoration: 'underline', cursor: 'pointer', padding: 0 }}
                        >
                            View Evaluation Report
                        </button>
                    )}
                    <span>Run: {runDetail.run.run_id.substring(0, 8)} | Config: {runDetail.run.config_version}</span>
                </div>
            </div>
            
            <HeroPanel 
                total={total} 
                autoCount={autoCount} 
                topConfidence={0} 
                isLoading={isLoading} 
            />
            
            <RateStrip 
                autoCount={autoCount}
                reviewCount={reviewCount}
                unmatchedCount={unmatchedCount}
                total={total}
                isLoading={isLoading} 
            />
            
            <div style={{ padding: '0.5rem', background: 'var(--surface-deep)', fontSize: '11px', color: 'var(--text-muted)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                Proposals only. Deterministic results remain immutable; reviewer actions are recorded separately.
            </div>

            <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                    onClick={() => setFilter('all')}
                    style={{
                        background: filter === 'all' ? 'var(--surface-inset)' : 'transparent',
                        color: filter === 'all' ? 'var(--text-primary)' : 'var(--text)',
                        border: `1px solid ${filter === 'all' ? 'var(--border)' : 'transparent'}`,
                        padding: '4px 12px',
                        cursor: 'pointer',
                        borderRadius: '4px',
                        fontSize: '12px'
                    }}
                >
                    All {total}
                </button>
                <button
                    onClick={() => setFilter('auto')}
                    style={{
                        background: filter === 'auto' ? 'var(--surface-inset)' : 'transparent',
                        color: filter === 'auto' ? 'var(--text-primary)' : 'var(--text)',
                        border: `1px solid ${filter === 'auto' ? 'var(--border)' : 'transparent'}`,
                        padding: '4px 12px',
                        cursor: 'pointer',
                        borderRadius: '4px',
                        fontSize: '12px'
                    }}
                >
                    Auto {autoCount}
                </button>
                <button
                    onClick={() => setFilter('review')}
                    style={{
                        background: filter === 'review' ? 'var(--surface-inset)' : 'transparent',
                        color: filter === 'review' ? 'var(--text-primary)' : 'var(--text)',
                        border: `1px solid ${filter === 'review' ? 'var(--border)' : 'transparent'}`,
                        padding: '4px 12px',
                        cursor: 'pointer',
                        borderRadius: '4px',
                        fontSize: '12px'
                    }}
                >
                    Review {reviewCount}
                </button>
                <button
                    onClick={() => setFilter('unmatched')}
                    style={{
                        background: filter === 'unmatched' ? 'var(--surface-inset)' : 'transparent',
                        color: filter === 'unmatched' ? 'var(--text-primary)' : 'var(--text)',
                        border: `1px solid ${filter === 'unmatched' ? 'var(--border)' : 'transparent'}`,
                        padding: '4px 12px',
                        cursor: 'pointer',
                        borderRadius: '4px',
                        fontSize: '12px'
                    }}
                >
                    Unmatched {unmatchedCount}
                </button>
            </div>

            {!isLoading && filteredRecords.length > 0 && (
                <LedgerTable 
                    records={filteredRecords} 
                    selectedId={selectedRecordId}
                    onSelect={setSelectedRecordId} 
                />
            )}
        </div>
    );
};
