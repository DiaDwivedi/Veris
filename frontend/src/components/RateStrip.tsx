import React from 'react';

interface RateStripProps {
    autoRate: number;
    reviewRate: number;
    unmatchedRate: number;
    isLoading: boolean;
}

export const RateStrip: React.FC<RateStripProps> = ({ autoRate, reviewRate, unmatchedRate, isLoading }) => {
    return (
        <div style={{
            display: 'flex',
            flexDirection: 'row',
            gap: '2rem',
            padding: '1rem 0',
            flexWrap: 'wrap'
        }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span className="serif" style={{ fontSize: '20px', color: 'black' }}>
                    {isLoading ? '-' : autoRate}%
                </span>
                <span style={{ fontSize: '12px', color: 'var(--muted-gray)' }}>automatic</span>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span className="serif" style={{ fontSize: '20px', color: 'black' }}>
                    {isLoading ? '-' : reviewRate}%
                </span>
                <span style={{ fontSize: '12px', color: 'var(--muted-gray)' }}>review</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span className="serif" style={{ fontSize: '20px', color: 'black' }}>
                    {isLoading ? '-' : unmatchedRate}%
                </span>
                <span style={{ fontSize: '12px', color: 'var(--muted-gray)' }}>unmatched</span>
            </div>
        </div>
    );
};
