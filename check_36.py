import csv

def main():
    txns = []
    with open('data/dev_transactions.csv', encoding='utf-8') as f:
        for r in csv.reader(f):
            if r[0] == 'TXN_0036':
                txns.append(r)
                
    ords = []
    with open('data/dev_orders.csv', encoding='utf-8') as f:
        for r in csv.reader(f):
            if r[0] == 'ORD_0036':
                ords.append(r)
                
    print('TXN_0036:', txns[0] if txns else None)
    print('ORD_0036:', ords[0] if ords else None)
    
if __name__ == '__main__':
    main()
