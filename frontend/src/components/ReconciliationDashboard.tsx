import React from 'react';
import type { BankRecord, WrappedReconciliationResult } from '../types';
import { HeroPanel } from './HeroPanel';
import { RateStrip } from './RateStrip';
import { LedgerTable } from './LedgerTable';

interface ReconciliationDashboardProps {
    transactions: BankRecord[];
    results: WrappedReconciliationResult[];
    isLoading: boolean;
}

export const ReconciliationDashboard: React.FC<ReconciliationDashboardProps> = ({ transactions, results, isLoading }) => {
    
    let total = 0;
    let autoCount = 0;
    let reviewCount = 0;
    let unmatchedCount = 0;
    let topConfidence = 0;

    if (!isLoading && results.length > 0) {
        total = results.length;
        
        results.forEach(wrapped => {
            const res = wrapped.deterministic_result;
            // Note: manual overrides don't change the auto/review/unmatched count natively here,
            // we leave the deterministics intact for the hero panel statistics.
            if (res.status === 'auto') autoCount++;
            else if (res.status === 'review') reviewCount++;
            else if (res.status === 'unmatched') unmatchedCount++;
            
            if (res.candidate && res.candidate.confidence_score > topConfidence) {
                topConfidence = res.candidate.confidence_score;
            }
        });
    }

    const autoRate = total > 0 ? Math.round((autoCount / total) * 100) : 0;
    const reviewRate = total > 0 ? Math.round((reviewCount / total) * 100) : 0;
    const unmatchedRate = total > 0 ? Math.round((unmatchedCount / total) * 100) : 0;

    return (
        <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '2rem' }}>
            <HeroPanel 
                total={total} 
                autoCount={autoCount} 
                topConfidence={topConfidence} 
                isLoading={isLoading} 
            />
            
            <RateStrip 
                autoRate={autoRate} 
                reviewRate={reviewRate} 
                unmatchedRate={unmatchedRate} 
                isLoading={isLoading} 
            />
            
            {!isLoading && results.length > 0 && (
                <LedgerTable transactions={transactions} results={results} />
            )}
        </div>
    );
};
