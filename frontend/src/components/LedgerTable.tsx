import React, { useState } from 'react';
import type { BankRecord, WrappedReconciliationResult } from '../types';
import { LedgerRow } from './LedgerRow';

interface LedgerTableProps {
    transactions: BankRecord[];
    results: WrappedReconciliationResult[];
}

export const LedgerTable: React.FC<LedgerTableProps> = ({ transactions, results }) => {
    const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

    const handleToggle = (index: number) => {
        setExpandedIndex(prev => prev === index ? null : index);
    };

    return (
        <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            marginTop: '1rem',
            textAlign: 'left',
            fontFamily: 'var(--font-sans)',
            fontSize: '14px'
        }}>
            <thead>
                <tr>
                    <th style={{ borderBottom: '2px solid var(--body-ink)', padding: '10px 0', paddingLeft: '8px', fontWeight: 'normal', color: 'var(--muted-gray)' }}>Transaction</th>
                    <th style={{ borderBottom: '2px solid var(--body-ink)', padding: '10px 0', fontWeight: 'normal', color: 'var(--muted-gray)' }}>Matched to</th>
                    <th style={{ borderBottom: '2px solid var(--body-ink)', padding: '10px 0', textAlign: 'right', fontWeight: 'normal', color: 'var(--muted-gray)' }}>Confidence</th>
                    <th style={{ borderBottom: '2px solid var(--body-ink)', padding: '10px 0', textAlign: 'right', paddingRight: '8px', fontWeight: 'normal', color: 'var(--muted-gray)' }}>Outcome</th>
                </tr>
            </thead>
            <tbody>
                {transactions.map((txn, index) => (
                    <LedgerRow 
                        key={txn.record_id}
                        transaction={txn}
                        result={results[index]}
                        isExpanded={expandedIndex === index}
                        onToggle={() => handleToggle(index)}
                    />
                ))}
            </tbody>
        </table>
    );
};
