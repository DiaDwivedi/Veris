export type TransactionSource = "merchant" | "bank";
export type MatchStatus = "auto" | "review" | "unmatched";

export interface TransactionRecord {
    record_id: string;
    amount: number;
    currency?: string;
    transaction_date: string;
    description: string;
    reference_id?: string | null;
    customer_id?: string | null;
    order_id?: string | null;
    invoice_id?: string | null;
}

export interface MerchantRecord extends TransactionRecord {
    source: "merchant";
}

export interface BankRecord extends TransactionRecord {
    source: "bank";
}

export interface SignalScore {
    earned: number;
    max: number;
    outcome: string;
}

export interface MatchCandidate {
    merchant_record: MerchantRecord;
    bank_record: BankRecord;
    confidence_score: number;
    matched_rules: string[];
}

export interface ReconciliationResult {
    candidate: MatchCandidate | null;
    status: MatchStatus;
    audit_trail: string[];
    why: string;
    explanation: string;
    explanation_source: string;
    routing_reason: string | null;
    signal_scores: Record<string, SignalScore>;
    competing_candidates: MatchCandidate[];
}

export interface BatchReconcileRequest {
    transactions: BankRecord[];
    orders: MerchantRecord[];
}

export interface OverrideRecordV2 {
    override_id: string;
    action: "approve" | "reject";
    candidate_id?: string | null;
    reviewer_note?: string | null;
    created_at: string;
}

export interface RecordDetail {
    transaction_id: string;
    deterministic_result: ReconciliationResult;
    override_history: OverrideRecordV2[];
}

export interface RunSummary {
    run_id: string;
    status: string;
    created_at: string;
    config_version: string;
    batch_size: number;
}

export interface RunDetailResponse {
    run: RunSummary;
    records: RecordDetail[];
}

export interface RunCreationResponse {
    run_id: string;
    status: string;
    summary: {
        total_processed: number;
    };
}
