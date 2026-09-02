import React from 'react';

interface HeroPanelProps {
    total: number;
    autoCount: number;
    topConfidence: number;
    isLoading: boolean;
}

export const HeroPanel: React.FC<HeroPanelProps> = ({ total, autoCount, topConfidence, isLoading }) => {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const batchId = "BATCH-001";
    
    const displayAuto = isLoading ? "-" : autoCount;
    const displayTotal = isLoading ? "-" : total;
    const displayConf = isLoading ? "-" : Math.round(topConfidence);

    return (
        <div style={{
            backgroundColor: 'var(--hero-bg)',
            padding: '2.25rem 2rem',
            borderRadius: '4px',
            color: 'var(--hero-muted-label)',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            fontFamily: 'var(--font-sans)',
            marginBottom: '2rem'
        }}>
            <div style={{ fontSize: '12px' }}>
                Batch {batchId} — {isLoading ? '-' : total} records, closed at {timestamp}
            </div>
            
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '2rem'
            }}>
                <div>
                    <div style={{
                        display: 'flex',
                        alignItems: 'baseline',
                        gap: '4px'
                    }}>
                        <span className="serif" style={{
                            fontSize: '76px',
                            color: 'var(--primary-accent)',
                            lineHeight: 0.95
                        }}>
                            {displayAuto}
                        </span>
                        <span className="serif" style={{
                            fontSize: '32px',
                            color: 'var(--hero-secondary-number)',
                            lineHeight: 0.95
                        }}>
                            /{displayTotal}
                        </span>
                    </div>
                    <div style={{
                        fontSize: '14px',
                        color: 'var(--hero-muted-subtext)',
                        marginTop: '0.5rem'
                    }}>
                        closed automatically. the rest waited for a human, on purpose.
                    </div>
                </div>

                <div style={{
                    width: '104px',
                    height: '104px',
                    borderRadius: '50%',
                    border: '3px solid var(--primary-accent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transform: 'rotate(-9deg)'
                }}>
                    <div style={{
                        width: '88px',
                        height: '88px',
                        borderRadius: '50%',
                        border: '1px solid var(--primary-accent)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--primary-accent)'
                    }}>
                        <span className="tabular-nums serif" style={{ fontSize: '24px', lineHeight: 1 }}>
                            {displayConf}%
                        </span>
                        <span className="uppercase" style={{ fontSize: '13px', letterSpacing: '2px', lineHeight: 1, marginTop: '2px' }}>
                            MATCH
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
};
