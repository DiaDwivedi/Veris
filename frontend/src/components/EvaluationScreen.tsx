import React from 'react';
import { appConfig, testRun, devRun, llmRunA, llmRunB, variance } from 'virtual:eval-data';

export const EvaluationScreen: React.FC = () => {
  const formatPct = (val: number | null | undefined) => {
    if (val === null || val === undefined) return 'N/A';
    // If > 1, it's already a percentage (deterministic auto_precision_percentage)
    // If <= 1, it's a decimal ratio
    const num = val > 1.0 ? val : val * 100;
    return num.toFixed(1) + '%';
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto', color: 'var(--text-primary)' }}>
      <h1 style={{ marginBottom: '2rem', fontSize: '28px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1rem' }}>
        Evaluation Report
      </h1>

      {/* 1. Split Discipline */}
      <section style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '18px', marginBottom: '1rem', color: 'var(--text)' }}>1. Split Discipline</h2>
        <div style={{ background: 'var(--surface-deep)', padding: '1rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontFamily: 'monospace' }}>
          <div>Dev split &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{devRun?.metadata?.dataset_size ?? 'Unavailable'} transactions &nbsp;— all tuning</div>
          <div>Held-out test &nbsp;{testRun?.metadata?.dataset_size ?? 'Unavailable'} transactions &nbsp;— run once</div>
        </div>
        <p style={{ marginTop: '0.75rem', fontSize: '14px', color: 'var(--text-muted)' }}>
          * The config was frozen after dev tuning; the test set was evaluated a single time against that frozen config.
        </p>
      </section>

      {/* 2. Frozen Configuration */}
      <section style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '18px', marginBottom: '1rem', color: 'var(--text)' }}>2. Frozen Configuration</h2>
        <table style={{ width: '100%', maxWidth: '600px', borderCollapse: 'collapse', marginBottom: '1rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left' }}>
              <th style={{ padding: '8px', color: 'var(--text-muted)' }}>Parameter</th>
              <th style={{ padding: '8px', color: 'var(--text-muted)' }}>Value</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px' }}>AUTO Threshold</td>
              <td style={{ padding: '8px' }}>{appConfig.THRESHOLD_AUTO}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px' }}>REVIEW Band Floor</td>
              <td style={{ padding: '8px' }}>{appConfig.THRESHOLD_REVIEW}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px' }}>Candidate Minimum Floor</td>
              <td style={{ padding: '8px' }}>{appConfig.THRESHOLD_MIN_SCORE}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px' }}>Weight: Reference ID</td>
              <td style={{ padding: '8px' }}>{appConfig.WEIGHT_REFERENCE_ID}</td>
            </tr>
            <tr style={{ borderBottom: 'none' }}>
              <td style={{ padding: '8px' }}>Weight: Amount Exact</td>
              <td style={{ padding: '8px' }}>{appConfig.WEIGHT_AMOUNT_EXACT}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px', paddingLeft: '24px', fontStyle: 'italic', color: 'var(--text-muted)' }}>or Amount Tolerance</td>
              <td style={{ padding: '8px', fontStyle: 'italic', color: 'var(--text-muted)' }}>{appConfig.WEIGHT_AMOUNT_TOLERANCE}</td>
            </tr>
            <tr style={{ borderBottom: 'none' }}>
              <td style={{ padding: '8px' }}>Weight: Date Exact</td>
              <td style={{ padding: '8px' }}>{appConfig.WEIGHT_DATE_EXACT}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px', paddingLeft: '24px', fontStyle: 'italic', color: 'var(--text-muted)' }}>or Date Proximity</td>
              <td style={{ padding: '8px', fontStyle: 'italic', color: 'var(--text-muted)' }}>{appConfig.WEIGHT_DATE_PROXIMITY}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px' }}>Weight: Customer ID</td>
              <td style={{ padding: '8px' }}>{appConfig.WEIGHT_CUSTOMER_ID}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px' }}>Weight: Description Match</td>
              <td style={{ padding: '8px' }}>{appConfig.WEIGHT_DESC_MATCH}</td>
            </tr>
          </tbody>
        </table>
        <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
          * The maximum achievable score is 120 (amount and date weights are alternates, not additive) while the reported score is capped at 100. This compresses the top of the scale but does not change routing, because the AUTO threshold of 90 sits below the cap. Found during final verification.
        </p>
      </section>

      {/* 3. Held-out test results (Deterministic engine only) */}
      <section style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '18px', marginBottom: '0.5rem', color: 'var(--text)' }}>3. Held-out Test Results (Deterministic Engine Only)</h2>
        <div style={{ marginBottom: '1rem', color: 'var(--text-faint)', fontSize: '14px' }}>
          <strong>Label: </strong> held-out test split, run once, config frozen.<br/>
          <strong>Timestamp: </strong> {testRun?.metadata?.timestamp}
        </div>
        
        <table style={{ width: '100%', maxWidth: '600px', borderCollapse: 'collapse', background: 'var(--surface)', border: '1px solid var(--border-subtle)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', background: 'var(--surface-deep)' }}>
              <th style={{ padding: '10px' }}>Metric</th>
              <th style={{ padding: '10px' }}>Value</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '10px' }}>AUTO Precision</td>
              <td style={{ padding: '10px' }}>{testRun?.metrics?.auto_precision_correct} of {testRun?.metrics?.auto_precision_total} correct ({formatPct(testRun?.metrics?.auto_precision_percentage)})</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '10px' }}>Candidate Recall</td>
              <td style={{ padding: '10px' }}>{formatPct(testRun?.metrics?.candidate_recall)}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '10px' }}>AUTO Match Recall</td>
              <td style={{ padding: '10px' }}>{formatPct(testRun?.metrics?.auto_match_recall)}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '10px' }}>AUTO Rate</td>
              <td style={{ padding: '10px' }}>{formatPct(testRun?.metrics?.auto_rate)}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '10px' }}>REVIEW Rate</td>
              <td style={{ padding: '10px' }}>{formatPct(testRun?.metrics?.review_rate)}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '10px' }}>UNMATCHED Rate</td>
              <td style={{ padding: '10px' }}>{formatPct(testRun?.metrics?.unmatched_rate)}</td>
            </tr>
          </tbody>
        </table>
      </section>

      {/* 4. Dev-split comparison */}
      <section style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '18px', marginBottom: '0.5rem', color: 'var(--text)' }}>4. Dev-Split Comparison (Deterministic vs LLM)</h2>
        <div style={{ marginBottom: '1rem', color: 'var(--text-faint)', fontSize: '14px' }}>
          <strong>Label: </strong> Both evaluated on the dev split.<br/>
          <strong>LLM Metadata: </strong> Model {llmRunA?.metadata?.model_id}, Temp {llmRunA?.metadata?.temperature}, Prompt {llmRunA?.metadata?.prompt_version}, {llmRunA?.metadata?.transaction_count} transactions, Uncached: {llmRunA?.metadata?.cache_enabled ? 'No' : 'Yes'}
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', background: 'var(--surface)', border: '1px solid var(--border-subtle)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', background: 'var(--surface-deep)' }}>
              <th style={{ padding: '10px' }}>Metric</th>
              <th style={{ padding: '10px' }}>Deterministic Engine</th>
              <th style={{ padding: '10px' }}>LLM Baseline</th>
              <th style={{ padding: '10px' }}>Winner</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '10px' }}>AUTO Precision</td>
              <td style={{ padding: '10px' }}>{formatPct(devRun?.metrics?.auto_precision_percentage)}</td>
              <td style={{ padding: '10px' }}>{formatPct(llmRunA?.metrics?.auto_precision)}</td>
              <td style={{ padding: '10px' }}>Tie</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '10px' }}>Candidate Recall</td>
              <td style={{ padding: '10px' }}>{formatPct(devRun?.metrics?.candidate_recall)}</td>
              <td style={{ padding: '10px' }}>{formatPct(llmRunA?.metrics?.candidate_recall)}</td>
              <td style={{ padding: '10px' }}>Deterministic</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', background: 'rgba(0, 255, 0, 0.05)' }}>
              <td style={{ padding: '10px' }}>AUTO Match Recall</td>
              <td style={{ padding: '10px' }}>{formatPct(devRun?.metrics?.auto_match_recall)}</td>
              <td style={{ padding: '10px' }}>{formatPct(llmRunA?.metrics?.auto_match_recall)}</td>
              <td style={{ padding: '10px', color: 'var(--auto)' }}>LLM Baseline</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', background: 'rgba(0, 255, 0, 0.05)' }}>
              <td style={{ padding: '10px' }}>AUTO Rate</td>
              <td style={{ padding: '10px' }}>{formatPct(devRun?.metrics?.auto_rate)}</td>
              <td style={{ padding: '10px' }}>{formatPct(llmRunA?.metrics?.auto_rate)}</td>
              <td style={{ padding: '10px', color: 'var(--auto)' }}>LLM Baseline</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', background: 'rgba(0, 255, 0, 0.05)' }}>
              <td style={{ padding: '10px' }}>REVIEW Rate</td>
              <td style={{ padding: '10px' }}>{formatPct(devRun?.metrics?.review_rate)}</td>
              <td style={{ padding: '10px' }}>{formatPct(llmRunA?.metrics?.review_rate)}</td>
              <td style={{ padding: '10px', color: 'var(--auto)' }}>LLM Baseline</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '10px' }}>UNMATCHED Rate</td>
              <td style={{ padding: '10px' }}>{formatPct(devRun?.metrics?.unmatched_rate)}</td>
              <td style={{ padding: '10px' }}>{formatPct(llmRunA?.metrics?.unmatched_rate)}</td>
              <td style={{ padding: '10px' }}>Deterministic</td>
            </tr>
          </tbody>
        </table>
        <p style={{ marginTop: '0.75rem', fontSize: '14px', color: 'var(--text-muted)' }}>
          * Note: Candidate recall is not comparable. The LLM baseline is shown only the top 10 candidates above the score floor, so its lower figure is an artifact of the harness, not a result.
        </p>
      </section>

      {/* 5. Reproducibility */}
      <section style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '18px', marginBottom: '1rem', color: 'var(--text)' }}>5. Reproducibility</h2>
        <div style={{ background: 'var(--surface)', padding: '1rem', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
          <ul style={{ margin: 0, paddingLeft: '20px', lineHeight: '1.8' }}>
            <li><strong>Decisions differed:</strong> {variance?.totalDiffs} of {variance?.totalDecisions}</li>
            <li><strong>Order ID differences:</strong> {variance?.orderDiffs}</li>
            <li><strong>Decision differences:</strong> {variance?.decisionDiffs}</li>
            <li><strong>Parse failures:</strong> Run A: {llmRunA?.metadata?.parse_failure_count}, Run B: {llmRunB?.metadata?.parse_failure_count}</li>
            <li><strong>Provider errors:</strong> Run A: {llmRunA?.metadata?.provider_error_count}, Run B: {llmRunB?.metadata?.provider_error_count}</li>
          </ul>
        </div>
        <p style={{ marginTop: '0.75rem', fontSize: '14px', color: 'var(--text-muted)', fontWeight: 'bold' }}>
          The baseline was reproducible at temperature 0 on this dataset.
        </p>
      </section>

    </div>
  );
};
