import React from 'react';
import type { RecordDetail } from '../types';
import { LedgerRow } from './LedgerRow';

interface LedgerTableProps {
    records: RecordDetail[];
    selectedId: string | null;
    onSelect: (id: string) => void;
}

export const LedgerTable: React.FC<LedgerTableProps> = ({ records, selectedId, onSelect }) => {
    return (
        <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            tableLayout: 'fixed',
            marginTop: '1rem',
            textAlign: 'left',
            fontFamily: 'var(--font-sans)',
            fontSize: '13px'
        }}>
            <thead style={{ position: 'sticky', top: 0, backgroundColor: 'var(--bg)', zIndex: 1 }}>
                <tr>
                    <th style={{ borderBottom: '1px solid var(--border-subtle)', padding: '4px 8px', fontWeight: 'bold', color: 'var(--text-muted)', width: '15%' }}>Transaction</th>
                    <th style={{ borderBottom: '1px solid var(--border-subtle)', padding: '4px 8px', fontWeight: 'bold', color: 'var(--text-muted)', width: '15%' }}>Proposed Match</th>
                    <th style={{ borderBottom: '1px solid var(--border-subtle)', padding: '4px 8px', fontWeight: 'bold', color: 'var(--text-muted)', width: '45%' }}>Why</th>
                    <th style={{ borderBottom: '1px solid var(--border-subtle)', padding: '4px 8px', textAlign: 'right', fontWeight: 'bold', color: 'var(--text-muted)', width: '10%' }}>Score</th>
                    <th style={{ borderBottom: '1px solid var(--border-subtle)', padding: '4px 8px', textAlign: 'right', fontWeight: 'bold', color: 'var(--text-muted)', width: '15%' }}>Decision</th>
                </tr>
            </thead>
            <tbody>
                {records.map((rec) => (
                    <LedgerRow 
                        key={rec.transaction_id}
                        record={rec}
                        isSelected={selectedId === rec.transaction_id}
                        onSelect={() => onSelect(rec.transaction_id)}
                    />
                ))}
            </tbody>
        </table>
    );
};
