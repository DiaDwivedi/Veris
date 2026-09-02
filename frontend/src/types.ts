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
}

export interface BatchReconcileRequest {
    transactions: BankRecord[];
    orders: MerchantRecord[];
}

export interface OverrideRecord {
    action: "approve" | "reject";
    timestamp: string;
}

export interface WrappedReconciliationResult {
    deterministic_result: ReconciliationResult;
    manual_override: OverrideRecord | null;
}

export interface BatchReconcileResponseV2 {
    results: WrappedReconciliationResult[];
}
