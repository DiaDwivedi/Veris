import { render, screen, fireEvent, cleanup, within, waitFor } from '@testing-library/react';
import { expect, test, describe, afterEach, vi } from 'vitest';
import { ReconciliationDashboard } from '../src/components/ReconciliationDashboard';
import { App } from '../src/App';
import React from 'react';
import type { BankRecord, WrappedReconciliationResult } from '../src/types';

describe('Reconciliation Dashboard', () => {
  afterEach(() => {
      cleanup();
      vi.restoreAllMocks();
  });

  const mockTransactions: BankRecord[] = [
    {
        record_id: "TXN_1",
        amount: 100.0,
        currency: "USD",
        transaction_date: "2026-09-02T00:00:00Z",
        description: "Test Bank Record 1",
        source: "bank"
    },
    {
        record_id: "TXN_2",
        amount: 200.0,
        currency: "USD",
        transaction_date: "2026-09-02T12:00:00Z",
        description: "Test Bank Record 2",
        source: "bank"
    }
  ];

  const mockResults: WrappedReconciliationResult[] = [
    {
        manual_override: null,
        deterministic_result: {
            status: "auto",
            candidate: {
                merchant_record: {
                    record_id: "ORD_1",
                    amount: 100.0,
                    transaction_date: "2026-09-02T00:00:00Z",
                    description: "Test Merchant Record 1",
                    source: "merchant"
                },
                bank_record: mockTransactions[0],
                confidence_score: 95.5,
                matched_rules: ["Amount Exact Match (+35)"]
            },
            audit_trail: ["All AUTO Safety Gates Passed"]
        }
    },
    {
        manual_override: null,
        deterministic_result: {
            status: "unmatched",
            candidate: null,
            audit_trail: ["Score 60.0 < 70. Routed to UNMATCHED."]
        }
    }
  ];

  test('Renders loading state dash correctly', () => {
    render(<ReconciliationDashboard transactions={[]} results={[]} isLoading={true} />);
    expect(screen.getAllByText('-').length).toBeGreaterThan(0);
  });

  test('Renders dashboard and zips data correctly', () => {
    render(<ReconciliationDashboard transactions={mockTransactions} results={mockResults} isLoading={false} />);
    
    // Check Hero Panel logic
    expect(screen.getByText('1')).toBeInTheDocument(); // auto count
    expect(screen.getByText('/2')).toBeInTheDocument(); // total count
    expect(screen.getByText('96%')).toBeInTheDocument(); // Math.round(95.5)

    // Check table rows zip matching
    expect(screen.getByText('TXN_1')).toBeInTheDocument();
    expect(screen.getByText('ORD_1')).toBeInTheDocument();
    expect(screen.getByText('95.5')).toBeInTheDocument();
    expect(screen.getByText('auto')).toBeInTheDocument();

    expect(screen.getByText('TXN_2')).toBeInTheDocument();
    const txn2Row = screen.getByText('TXN_2').closest('tr');
    expect(within(txn2Row!).getByText('unmatched')).toBeInTheDocument();
    // candidate is null for UNMATCHED, confidence should be '—'
    expect(screen.getAllByText('—').length).toBeGreaterThan(0); 
  });

  test('Row expansion is mutually exclusive', () => {
    render(<ReconciliationDashboard transactions={mockTransactions} results={mockResults} isLoading={false} />);
    
    // Rows
    const row1 = screen.getByText('TXN_1');
    const row2 = screen.getByText('TXN_2');

    // Click row 1
    fireEvent.click(row1);
    expect(screen.getByText('TXN_1, under auto')).toBeInTheDocument(); // Detail Panel header
    
    // Click row 2
    fireEvent.click(row2);
    // Row 1 detail panel should be closed
    expect(screen.queryByText('TXN_1, under auto')).not.toBeInTheDocument();
    // Row 2 detail panel should be open
    expect(screen.getByText('TXN_2, under unmatched')).toBeInTheDocument();
  });

  test('Override actions trigger API and update UI', async () => {
    global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ action: 'approve', timestamp: '2026-09-02T00:00:00Z' })
    });

    render(<ReconciliationDashboard transactions={mockTransactions} results={mockResults} isLoading={false} />);
    fireEvent.click(screen.getByText('TXN_1'));

    const approve = screen.getByText('Approve match');
    expect(approve.tagName).toBe('BUTTON');

    fireEvent.click(approve);

    // Verify fetch was called with correct payload
    expect(global.fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/overrides/approve', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ transaction_id: 'TXN_1', candidate_id: 'ORD_1' })
    }));

    // Wait for the UI to update to show timestamp
    await waitFor(() => {
        expect(screen.getByText(/✓ Manually approved on/i)).toBeInTheDocument();
    });
  });

  test('Renders 409 conflict gracefully', async () => {
    global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ detail: 'Conflict: transaction already overridden' })
    });

    render(<ReconciliationDashboard transactions={mockTransactions} results={mockResults} isLoading={false} />);
    fireEvent.click(screen.getByText('TXN_1'));

    const approve = screen.getByText('Approve match');
    fireEvent.click(approve);

    await waitFor(() => {
        expect(screen.getByText('Conflict: transaction already overridden')).toBeInTheDocument();
    });
  });
});
