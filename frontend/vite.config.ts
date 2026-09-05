import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import fs from 'fs'
import path from 'path'

function evalDataPlugin() {
  return {
    name: 'eval-data',
    resolveId(id: string) {
      if (id === 'virtual:eval-data') {
        return '\0virtual:eval-data'
      }
    },
    load(id: string) {
      if (id === '\0virtual:eval-data') {
        // config.py
        const configPy = fs.readFileSync(path.resolve(__dirname, '../app/config.py'), 'utf-8');
        const config: Record<string, number> = {};
        for (const line of configPy.split('\n')) {
           const match = line.match(/^([A-Z_]+)\s*=\s*([0-9.]+)/);
           if (match) config[match[1]] = parseFloat(match[2]);
        }
        
        // held out test
        const testRun = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../evaluation/results/evaluation_run_20260905_143611.json'), 'utf-8'));
        
        // most recent dev
        const resultsDir = path.resolve(__dirname, '../evaluation/results');
        const files = fs.readdirSync(resultsDir).filter(f => f.endsWith('.json') && !f.includes('143611'));
        files.sort((a,b) => fs.statSync(path.join(resultsDir, b)).mtimeMs - fs.statSync(path.join(resultsDir, a)).mtimeMs);
        const devRun = JSON.parse(fs.readFileSync(path.join(resultsDir, files[0]), 'utf-8'));
        
        // llm runs
        const llmRunA = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../evaluation/llm_baseline_flashlite_run_a.json'), 'utf-8'));
        const llmRunB = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../evaluation/llm_baseline_flashlite_run_b.json'), 'utf-8'));
        
        // compare runs logic
        let orderDiffs = 0;
        let decisionDiffs = 0;
        let totalDiffs = 0;
        const recordsA: any = {};
        for (const r of llmRunA.records) recordsA[r.transaction_id] = r;
        for (const r of llmRunB.records) {
            const ra = recordsA[r.transaction_id];
            if (!ra) continue;
            const diffOrder = ra.order_id !== r.order_id;
            const diffDecision = ra.decision !== r.decision;
            if (diffOrder) orderDiffs++;
            if (diffDecision) decisionDiffs++;
            if (diffOrder || diffDecision) totalDiffs++;
        }
        const variance = {
            totalDiffs,
            orderDiffs,
            decisionDiffs,
            totalDecisions: Object.keys(recordsA).length
        };
        
        return `
          export const appConfig = ${JSON.stringify(config)};
          export const testRun = ${JSON.stringify(testRun)};
          export const devRun = ${JSON.stringify(devRun)};
          export const llmRunA = ${JSON.stringify(llmRunA)};
          export const llmRunB = ${JSON.stringify(llmRunB)};
          export const variance = ${JSON.stringify(variance)};
        `;
      }
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), evalDataPlugin()],
  server: {
    fs: {
      allow: ['..']
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
