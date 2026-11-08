
# Progetto 1: Sistema di Transazioni Bancarie Distribuite con Mutua Esclusione a Token Ring

**Corso:** Intelligenza Artificiale Distribuita - Università San Raffaele Roma  
**Implementazione:** Python 3 - 4 nodi ATM su localhost - Token Ring

## Architettura e Teoria (PDF Lezioni p.351-362)

Il sistema implementa fedelmente l'algoritmo Token Ring per la mutua esclusione:

- **Topologia logica:** ATM1 → ATM2 → ATM3 → ATM4 → ATM1 (anello logico, rete fisica arbitraria su localhost)
- **Assunzioni:** N=4 processi, canali punto-a-punto TCP affidabili tra successori, esiste esattamente un token, CS non preemptive
- **Token:** Messaggio speciale JSON che circola continuamente. Solo il possessore può entrare in CS. Contiene saldo condiviso, seq number ed epoch (per tolleranza ai guasti come da p.359)
- **Correttezza:**
  - *Safety:* Al massimo un processo in CS perché al massimo un detentore del token (unicità token)
  - *Liveness:* Ogni richiesta è infine soddisfatta perché token circola in tempo finito (0..N hop)
  - *No starvation:* Rotazione garantisce possibilità per giro
  - *Ordinamento:* Non garantisce happened-before, ordine dipende da posizione token (come da esempio p.357)

## Risorsa Condivisa e Sezione Critica

- **Risorsa:** Saldo conto bancario unico (nessuna memoria condivisa, ogni nodo ha memoria privata)
- **Come è condiviso senza memoria condivisa:** Il saldo viaggia DENTRO il token. Ogni nodo legge il saldo dal token, valida, aggiorna atomicamente e scrive il nuovo valore nel token prima di inoltrarlo. Serializzazione garantita da mutua esclusione.
- **Transazione = Sezione Critica atomica:**
  1. Lettura saldo corrente dal token
  2. Validazione (prelievo solo se saldo >= importo)
  3. Aggiornamento saldo
  4. Scrittura nuovo valore nel token
  5. Log operazione

## Struttura File

```
atm_node.py         # Implementazione completa nodo ATM (server + client + logica CS)
requirements.txt    # Nessuna dipendenza esterna
start_demo.sh       # Script avvio rapido per test (opzionale)
README.md           # Questo file
```

## Esecuzione - Istruzioni Esatte (Requisito Consegna)

### Prerequisiti
- Python 3.8+ (consigliato 3.10)
- Sistema operativo: Windows / Linux / macOS
- 4 terminali / console separati
- Porte 5001-5004 libere su localhost

### Comandi per avviare i 4 nodi (OBBLIGATORI - da copiare esattamente)

**IMPORTANTE:** Avviare i nodi in ordine inverso (4,3,2,1) oppure tutti quasi contemporaneamente per evitare retry lunghi. Il sistema ha retry automatico.

**Terminale 1 - ATM1 (Initial Token Holder, saldo iniziale 1000, nessuna transazione):**
```bash
python atm_node.py --id 1 --port 5001 --succ-port 5002 --initial-holder --initial-balance 1000
```

**Terminale 2 - ATM2 (Prelievo 200 come da esempio specifica):**
```bash
python atm_node.py --id 2 --port 5002 --succ-port 5003 --transactions withdraw:200
```

**Terminale 3 - ATM3 (Deposito 100):**
```bash
python atm_node.py --id 3 --port 5003 --succ-port 5004 --transactions deposit:100
```

**Terminale 4 - ATM4 (Prelievo 500):**
```bash
python atm_node.py --id 4 --port 5004 --succ-port 5001 --transactions withdraw:500
```

**Comando con transazioni multiple (esempio avanzato):**
```bash
python atm_node.py --id 2 --port 5002 --succ-port 5003 --transactions withdraw:200,deposit:50,withdraw:100
```

### Associazione Nodo-Terminale

- Ogni terminale mostra chiaramente `[HH:MM:SS.mmm][ATMx]` nei log
- Titolo del terminale: si consiglia di rinominare manualmente (es. "ATM1 - 5001")
- Log distinguibili: Ricezione token, Inoltro token, Inizio/Fine transazione, Saldo aggiornato
- Per riconoscere: ATM1 log iniziale `POSSESSO INIZIALE DEL TOKEN`, altri `RICEZIONE TOKEN`

### Sequenza di Esecuzione Attesa (Esempio Specifica)

Stato iniziale: Saldo 1000, Token in ATM1

1. ATM1 possiede token, nessuna transazione → inoltra a ATM2 (Saldo 1000)
2. ATM2 riceve token, esegue prelievo 200 → Saldo 800 → inoltra a ATM3
3. ATM3 riceve token, deposito 100 → Saldo 900 → inoltra a ATM4
4. ATM4 riceve token, prelievo 500 → Saldo 400 → inoltra a ATM1
5. Token continua a circolare (liveness dimostrata), nessun altro prelievo

Log mostrano assenza di transazioni concorrenti (Safety).

## Logging Richiesto (Implementato)

Ogni nodo registra:
- ✅ Ricezione token con seq e balance
- ✅ Inoltro token al successore
- ✅ Inizio transazione (lettura saldo)
- ✅ Fine transazione (scrittura nuovo saldo)
- ✅ Saldo aggiornato
- ✅ Movimento token e assenza concorrenza

## Video Dimostrativo - Cosa Mostrare

1. Aprire 4 terminali affiancati
2. Avviare i 4 comandi sopra (mostrare che ogni nodo è in console separata)
3. Evidenziare circolazione token con timestamp
4. Mostrare esecuzione transazioni in ordine ATM2→ATM3→ATM4
5. Mostrare saldo finale 400 coerente
6. Lasciare circolare token per 10-20 secondi per dimostrare liveness
7. Ctrl+C per chiusura

## Gestione Guasti (Teoria PDF p.359 - Implementata parzialmente per robustezza)

- Retry automatico di connessione al successore (max 20 tentativi con backoff)
- Epoch nel token per futura estensione di rigenerazione token in caso di crash del detentore
- Server resiliente a disconnessioni

## Codice Commentato - Punti Chiave

- `start_server()`: Socket TCP server, ricezione token JSON line-delimited, queue thread-safe
- `forward_token()`: Client TCP con retry, garantisce consegna al successore logico
- `execute_transaction()`: Sezione critica atomica, validazione prelievo, log
- `run()`: Loop principale token ring, initial holder crea token, altri attendono

Nessuna variabile globale condivisa, solo scambio messaggi.
