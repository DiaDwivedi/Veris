declare module 'virtual:eval-data' {
  export const appConfig: Record<string, number>;
  export const testRun: any;
  export const devRun: any;
  export const llmRunA: any;
  export const llmRunB: any;
  export const variance: {
    totalDiffs: number;
    orderDiffs: number;
    decisionDiffs: number;
    totalDecisions: number;
  };
}
