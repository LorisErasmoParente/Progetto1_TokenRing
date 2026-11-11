
#!/usr/bin/env python3
"""
Progetto 1: Sistema di Transazioni Bancarie Distribuite con Mutua Esclusione a Token Ring
Studente: Loris Erasmo Parente - Matricola 0322600005
Corso: Intelligenza Artificiale Distribuita - Universita San Raffaele Roma
Linguaggio: Python 3 (solo librerie standard)

Descrizione:
- 4 nodi ATM in anello logico su localhost, comunicazione tramite socket TCP.
- Mutua esclusione implementata esclusivamente tramite algoritmo Token Ring.
- Ogni nodo conosce solo il proprio successore.
- Nel sistema esiste un unico token che circola continuamente:
  il possesso del token concede il diritto esclusivo di entrare
  nella sezione critica ed eseguire una transazione.
- Nessuna memoria condivisa: ogni nodo ha memoria privata.
  Il saldo viaggia dentro il token.
"""

import socket
import threading
import json
import time
import argparse
import sys
import queue
from datetime import datetime

# Configurazione logging colorata opzionale
def log_msg(node_id, message):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}][ATM{node_id}] {message}", flush=True)

class ATMNode:
    def __init__(self, node_id, port, succ_host, succ_port, initial_holder, initial_balance, transactions):
        self.node_id = node_id
        self.port = port
        self.succ_host = succ_host
        self.succ_port = succ_port
        self.initial_holder = initial_holder
        self.initial_balance = initial_balance
        # Coda transazioni pendenti: lista di dict {"type": "deposit"/"withdraw", "amount": int}
        self.transactions = transactions
        self.token_queue = queue.Queue()
        self.running = True
        self.seq_counter = 0
        self.server_socket = None

    def parse_transactions(self, trans_str):
        """Parsa stringa tipo 'withdraw:200,deposit:100'"""
        result = []
        if not trans_str:
            return result
        for item in trans_str.split(','):
            item = item.strip()
            if not item:
                continue
            try:
                typ, amt = item.split(':')
                typ = typ.strip().lower()
                amt = int(amt.strip())
                if typ in ('deposit', 'deposito', 'prelievo', 'withdraw', 'withdrawal'):
                    # normalizza
                    if typ in ('prelievo', 'withdraw', 'withdrawal'):
                        typ = 'withdraw'
                    else:
                        typ = 'deposit'
                    result.append({'type': typ, 'amount': amt})
                else:
                    log_msg(self.node_id, f"Transazione non valida ignorata: {item}")
            except Exception as e:
                log_msg(self.node_id, f"Errore parsing transazione '{item}': {e}")
        return result

    def start_server(self):
        """Thread server TCP che riceve il TOKEN"""
        def server_loop():
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(('127.0.0.1', self.port))
                self.server_socket.listen(5)
                log_msg(self.node_id, f"Nodo ATM{self.node_id} in ascolto su 127.0.0.1:{self.port} | Successore -> {self.succ_host}:{self.succ_port}")
                while self.running:
                    try:
                        self.server_socket.settimeout(1.0)
                        conn, addr = self.server_socket.accept()
                        with conn:
                            data = b""
                            conn.settimeout(5.0)
                            while True:
                                chunk = conn.recv(4096)
                                if not chunk:
                                    break
                                data += chunk
                                if b"\n" in data:
                                    break
                            if data:
                                try:
                                    # supporta multipli messaggi separati da newline
                                    for line in data.decode('utf-8').strip().split('\n'):
                                        if not line.strip():
                                            continue
                                        token = json.loads(line)
                                        if token.get('type') == 'TOKEN':
                                            self.token_queue.put(token)
                                except Exception as e:
                                    log_msg(self.node_id, f"Errore parsing messaggio: {e} | raw={data[:200]}")
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.running:
                            log_msg(self.node_id, f"Errore server: {e}")
                            time.sleep(0.5)
            except Exception as e:
                log_msg(self.node_id, f"IMPOSSIBILE avviare server su porta {self.port}: {e}")
                sys.exit(1)

        t = threading.Thread(target=server_loop, daemon=True, name=f"Server-ATM{self.node_id}")
        t.start()
        return t

    def forward_token(self, token):
        """Inoltra il token al successore con retry affidabile"""
        max_retries = 20
        retry_delay = 0.5
        for attempt in range(1, max_retries + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3.0)
                    s.connect((self.succ_host, self.succ_port))
                    message = json.dumps(token) + "\n"
                    s.sendall(message.encode('utf-8'))
                    log_msg(self.node_id, f"Inoltro TOKEN [seq={token.get('seq')} balance={token.get('balance')}] -> ATM successore {self.succ_host}:{self.succ_port} (tentativo {attempt})")
                    return True
            except Exception as e:
                if attempt == 1 or attempt % 5 == 0:
                    log_msg(self.node_id, f"Successore non raggiungibile ({self.succ_host}:{self.succ_port}) tentativo {attempt}/{max_retries}: {e} - retry in {retry_delay}s")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.2, 3.0)
        log_msg(self.node_id, f"ERRORE CRITICO: impossibile inoltrare TOKEN dopo {max_retries} tentativi. Anello interrotto!")
        return False

    def execute_transaction(self, token):
        """Esecuzione atomica della sezione critica (transazione bancaria)"""
        if not self.transactions:
            return token

        trans = self.transactions.pop(0)
        t_type = trans['type']
        amount = trans['amount']

        log_msg(self.node_id, f"--- INIZIO TRANSAZIONE {t_type.upper()} {amount} ---")
        log_msg(self.node_id, f"Lettura saldo corrente: {token['balance']}")

        # Validazione e aggiornamento atomico
        current_balance = token['balance']
        if t_type == 'withdraw':
            if amount > current_balance:
                log_msg(self.node_id, f"VALIDAZIONE FALLITA: prelievo {amount} > saldo {current_balance} - Transazione annullata")
            else:
                new_balance = current_balance - amount
                # Simula atomicità: lettura, validazione, scrittura
                time.sleep(0.3)
                token['balance'] = new_balance
                log_msg(self.node_id, f"Prelievo {amount} eseguito. Nuovo saldo: {new_balance}")
        else:  # deposit
            new_balance = current_balance + amount
            time.sleep(0.3)
            token['balance'] = new_balance
            log_msg(self.node_id, f"Deposito {amount} eseguito. Nuovo saldo: {new_balance}")

        log_msg(self.node_id, f"Scrittura nuovo valore completata | Log operazione: ATM{self.node_id} {t_type} {amount} | Saldo={token['balance']}")
        log_msg(self.node_id, f"--- FINE TRANSAZIONE ---")
        return token

    def run(self):
        server_thread = self.start_server()
        time.sleep(1.0)  # attesa che tutti i server siano up

        # Se è initial holder, crea e inietta il token
        if self.initial_holder:
            token = {
                "type": "TOKEN",
                "balance": self.initial_balance,
                "seq": 0,
                "epoch": 1,  # contatore di epoca per gestione del token
                "origin": f"ATM{self.node_id}"
            }
            log_msg(self.node_id, f"*** POSSESSO INIZIALE DEL TOKEN *** Saldo iniziale={token['balance']} | seq={token['seq']} epoch={token['epoch']}")
            # Se ha transazione, eseguila prima di inoltrare, altrimenti inoltra subito
            time.sleep(1.5)
            if self.transactions:
                token = self.execute_transaction(token)
            else:
                log_msg(self.node_id, "Nessuna transazione pendente per ATM1 iniziale")
            
            token["seq"] += 1
            self.seq_counter = token["seq"]
            log_msg(self.node_id, f"ATM{self.node_id} rilascia TOKEN dopo elaborazione iniziale")
            self.forward_token(token)
        
        # Loop principale: ricezione e gestione token circolante
        try:
            while self.running:
                try:
                    # Attesa bloccante del token con timeout per permettere graceful shutdown
                    token = self.token_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                log_msg(self.node_id, f"*** RICEZIONE TOKEN *** da predecessore | seq={token.get('seq')} balance={token.get('balance')} epoch={token.get('epoch')}")
                
                # Correttezza: solo chi possiede token entra in CS
                # Sezione critica opzionale
                if self.transactions:
                    token = self.execute_transaction(token)
                else:
                    log_msg(self.node_id, "Nessuna transazione pendente -> inoltro immediato (come da specifica)")
                    time.sleep(0.2)  # simula bassa latenza di inoltro

                # Rilascio token
                token["seq"] = token.get("seq", 0) + 1
                self.seq_counter = token["seq"]
                # Piccola pausa per rendere visibile la circolazione nei log/video
                time.sleep(0.5)
                success = self.forward_token(token)
                if not success:
                    log_msg(self.node_id, "Mantengo token localmente per retry successivo")
                    self.token_queue.put(token)
                    time.sleep(2)

        except KeyboardInterrupt:
            log_msg(self.node_id, "Interruzione da tastiera (Ctrl+C) - Chiusura nodo")
        finally:
            self.running = False
            if self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
            log_msg(self.node_id, "Nodo terminato")

def main():
    parser = argparse.ArgumentParser(description="Nodo ATM - Token Ring Bancario Distribuito - Progetto 1")
    parser.add_argument('--id', type=int, required=True, choices=[1,2,3,4], help='ID nodo ATM (1-4)')
    parser.add_argument('--port', type=int, required=True, help='Porta di ascolto locale (es. 5001)')
    parser.add_argument('--succ-host', type=str, default='127.0.0.1', help='Host successore (default 127.0.0.1)')
    parser.add_argument('--succ-port', type=int, required=True, help='Porta successore (es. 5002)')
    parser.add_argument('--initial-holder', action='store_true', help='Questo nodo possiede inizialmente il token (solo ATM1)')
    parser.add_argument('--initial-balance', type=int, default=1000, help='Saldo iniziale se initial-holder (default 1000)')
    parser.add_argument('--transactions', type=str, default='', help='Transazioni pendenti: es. "withdraw:200,deposit:100"')

    args = parser.parse_args()

    # Validazione specifica Progetto 1
    if args.id == 1 and not args.initial_holder:
        print(f"ATTENZIONE: ATM1 dovrebbe avere --initial-holder secondo esempio progetto. Continuo comunque...")

    # Parsing transazioni
    # Se non fornite, usa scenario di esempio da specifica per dimostrazione
    transactions = []
    if args.transactions:
        # parsing manuale
        for item in args.transactions.split(','):
            item=item.strip()
            if not item: continue
            try:
                typ, amt = item.split(':')
                typ=typ.strip().lower()
                if typ in ('prelievo','withdraw','withdrawal'): typ='withdraw'
                else: typ='deposit'
                transactions.append({'type': typ, 'amount': int(amt.strip())})
            except:
                pass
    else:
        # Scenario di default conforme a specifica Progetto 1 - Esempio Dettagliato
        if args.id == 2:
            transactions = [{'type': 'withdraw', 'amount': 200}]
        elif args.id == 3:
            transactions = [{'type': 'deposit', 'amount': 100}]
        elif args.id == 4:
            transactions = [{'type': 'withdraw', 'amount': 500}]
        else:
            transactions = []

    log_msg(args.id, f"Avvio ATM{args.id} | Porta {args.port} -> Successore {args.succ_host}:{args.succ_port} | InitialHolder={args.initial_holder} | Transazioni={transactions}")

    node = ATMNode(
        node_id=args.id,
        port=args.port,
        succ_host=args.succ_host,
        succ_port=args.succ_port,
        initial_holder=args.initial_holder,
        initial_balance=args.initial_balance,
        transactions=transactions
    )
    node.run()

if __name__ == '__main__':
    main()
