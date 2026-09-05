import React from 'react';

interface RateStripProps {
    autoCount: number;
    reviewCount: number;
    unmatchedCount: number;
    total: number;
    isLoading: boolean;
}

export const RateStrip: React.FC<RateStripProps> = ({ autoCount, reviewCount, unmatchedCount, total, isLoading }) => {
    const autoRate = total > 0 ? Math.round((autoCount / total) * 100) : 0;
    const reviewRate = total > 0 ? Math.round((reviewCount / total) * 100) : 0;
    const unmatchedRate = total > 0 ? Math.round((unmatchedCount / total) * 100) : 0;

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'row',
            gap: '8px',
            marginBottom: '1rem',
            flexWrap: 'wrap'
        }}>
            <div style={{ 
                flex: 1,
                display: 'flex', 
                flexDirection: 'column', 
                gap: '4px',
                background: 'var(--auto-bg)',
                border: '1px solid var(--auto)',
                padding: '8px 12px',
                borderRadius: '4px'
            }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>Auto-Matched</span>
                <span className="tabular-nums" style={{ fontSize: '20px', color: 'var(--auto)', fontWeight: 'bold', lineHeight: 1 }}>
                    {isLoading ? '-' : autoCount}
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>{isLoading ? '-' : `${autoRate}%`}</span>
            </div>
            
            <div style={{ 
                flex: 1,
                display: 'flex', 
                flexDirection: 'column', 
                gap: '4px',
                background: 'var(--review-bg)',
                border: '1px solid var(--review-dark)',
                padding: '8px 12px',
                borderRadius: '4px'
            }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>Needs Review</span>
                <span className="tabular-nums" style={{ fontSize: '20px', color: 'var(--review)', fontWeight: 'bold', lineHeight: 1 }}>
                    {isLoading ? '-' : reviewCount}
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>{isLoading ? '-' : `${reviewRate}%`}</span>
            </div>

            <div style={{ 
                flex: 1,
                display: 'flex', 
                flexDirection: 'column', 
                gap: '4px',
                background: 'var(--surface-deep)',
                border: '1px solid var(--border-subtle)',
                padding: '8px 12px',
                borderRadius: '4px'
            }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>Unmatched</span>
                <span className="tabular-nums" style={{ fontSize: '20px', color: 'var(--text-primary)', fontWeight: 'bold', lineHeight: 1 }}>
                    {isLoading ? '-' : unmatchedCount}
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>{isLoading ? '-' : `${unmatchedRate}%`}</span>
            </div>
        </div>
    );
};
