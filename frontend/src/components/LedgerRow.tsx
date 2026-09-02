import React, { useState } from 'react';
import type { BankRecord, WrappedReconciliationResult, OverrideRecord } from '../types';
import { DetailPanel } from './DetailPanel';

interface LedgerRowProps {
    transaction: BankRecord;
    result: WrappedReconciliationResult;
    isExpanded: boolean;
    onToggle: () => void;
}

export const LedgerRow: React.FC<LedgerRowProps> = ({ transaction, result, isExpanded, onToggle }) => {
    const res = result.deterministic_result;
    const [override, setOverride] = useState<OverrideRecord | null>(result.manual_override);
    
    let statusText: string = res.status;
    let statusBorderColor = '';
    let statusTextColor = '';
    
    if (override) {
        statusText = override.action;
        statusBorderColor = override.action === 'approve' ? 'var(--auto-status)' : 'var(--muted-gray)';
        statusTextColor = override.action === 'approve' ? 'var(--auto-status)' : 'var(--muted-gray)';
    } else {
        const baseColor = res.status === 'auto' ? 'var(--auto-status)' : 
                          res.status === 'review' ? 'var(--review-status)' : 
                          'var(--faint-muted)';
                          
        statusTextColor = res.status === 'unmatched' ? 'var(--lighter-muted)' : baseColor;
        statusBorderColor = res.status === 'unmatched' ? 'var(--faint-muted)' : baseColor;
    }

    const matchedTo = res.candidate ? res.candidate.merchant_record.record_id : '—';
    const confidence = res.candidate ? res.candidate.confidence_score.toFixed(1) : '—';

    return (
        <React.Fragment>
            <tr 
                onClick={onToggle}
                style={{ 
                    borderBottom: '1px solid var(--table-hairlines)',
                    backgroundColor: isExpanded ? 'var(--selected-row-tint)' : 'transparent',
                    cursor: 'pointer'
                }}
            >
                <td className="tabular-nums" style={{ padding: '10px 0', paddingLeft: '8px' }}>
                    {transaction.record_id}
                </td>
                <td style={{ padding: '10px 0' }}>
                    {matchedTo}
                </td>
                <td className="tabular-nums" style={{ padding: '10px 0', textAlign: 'right' }}>
                    {confidence}
                </td>
                <td style={{ padding: '10px 0', textAlign: 'right', paddingRight: '8px' }}>
                    <span className="lowercase" style={{
                        display: 'inline-block',
                        border: `1px solid ${statusBorderColor}`,
                        color: statusTextColor,
                        padding: '2px 8px',
                        borderRadius: '20px',
                        fontSize: '11px',
                        backgroundColor: 'transparent'
                    }}>
                        {statusText}
                    </span>
                </td>
            </tr>
            {isExpanded && (
                <tr style={{ backgroundColor: 'var(--selected-row-tint)', borderBottom: '1px solid var(--table-hairlines)' }}>
                    <DetailPanel 
                        transaction={transaction} 
                        result={result} 
                        override={override}
                        setOverride={setOverride}
                    />
                </tr>
            )}
        </React.Fragment>
    );
};
