import os
import csv

def find_csvs():
    for root, dirs, files in os.walk('.'):
        if '.venv' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.csv'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        count = len(lines)
                        has_scenario = 'No'
                        if count > 0 and 'scenario' in lines[0]:
                            has_scenario = 'Yes'
                        print(f"{path}: {count} rows, scenario column: {has_scenario}")
                except Exception as e:
                    print(f"{path}: Error reading - {e}")

if __name__ == '__main__':
    find_csvs()
