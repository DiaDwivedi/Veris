import React from 'react';
import type { RecordDetail } from '../types';

interface LedgerRowProps {
    record: RecordDetail;
    isSelected: boolean;
    onSelect: () => void;
}

export const LedgerRow: React.FC<LedgerRowProps> = ({ record, isSelected, onSelect }) => {
    const res = record.deterministic_result;
    
    // Override history check
    const hasOverrides = record.override_history.length > 0;
    const latestOverride = hasOverrides ? record.override_history[record.override_history.length - 1] : null;
    
    let statusText: string = res.status;
    let statusBgColor = 'transparent';
    let statusTextColor = 'var(--text)';

    if (latestOverride) {
        statusText = latestOverride.action;
        if (latestOverride.action === 'approve') {
            statusTextColor = 'var(--auto)';
            statusBgColor = 'var(--auto-bg)';
        } else if (latestOverride.action === 'reject') {
            statusTextColor = 'var(--text-primary)';
            statusBgColor = 'var(--surface)';
        }
    } else {
        if (res.status === 'auto') {
            statusTextColor = 'var(--auto)';
            statusBgColor = 'var(--auto-bg)';
        } else if (res.status === 'review') {
            statusTextColor = 'var(--review)';
            statusBgColor = 'var(--review-bg)';
        } else if (res.status === 'unmatched') {
            statusTextColor = 'var(--unmatched-text)';
            statusBgColor = 'var(--unmatched-bg)';
        }
    }

    const matchedTo = res.candidate ? res.candidate.merchant_record.record_id : '—';
    const confidence = res.candidate ? Math.round(res.candidate.confidence_score) + '/100' : '—';
    const whyText = res.why || '—';

    return (
        <tr 
            onClick={onSelect}
            style={{ 
                borderBottom: '1px solid var(--border-subtle)',
                backgroundColor: isSelected ? 'var(--surface-deep)' : 'transparent',
                cursor: 'pointer'
            }}
        >
            <td className="tabular-nums" style={{ padding: '4px 8px', color: 'var(--text-primary)', fontSize: '12px' }}>
                {record.transaction_id}
            </td>
            <td className="tabular-nums" style={{ padding: '4px 8px', color: 'var(--text)', fontSize: '12px' }}>
                {matchedTo}
            </td>
            <td style={{ padding: '4px 8px', color: 'var(--text-primary)', fontSize: '12px', lineHeight: 1.2 }}>
                {whyText}
            </td>
            <td className="tabular-nums" style={{ padding: '4px 8px', textAlign: 'right', color: 'var(--text-primary)', fontWeight: 'bold', fontSize: '12px' }}>
                {confidence}
            </td>
            <td style={{ padding: '4px 8px', textAlign: 'right' }}>
                <span className="uppercase" style={{
                    display: 'inline-block',
                    color: statusTextColor,
                    backgroundColor: statusBgColor,
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '10px',
                    fontWeight: 'bold',
                    letterSpacing: '0.5px'
                }}>
                    {statusText}
                </span>
            </td>
        </tr>
    );
};
