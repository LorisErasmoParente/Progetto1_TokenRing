Elaborato del corso di Intelligenza Artificiale Distribuita, Università San Raffaele
Studente: Loris Erasmo Parente, matricola n° 0322600005

# Progetto 1: Sistema di Transazioni Bancarie Distribuite con Mutua Esclusione a Token Ring

**Linguaggio utilizzato:** Python 3

## Obiettivo del progetto

In questo progetto ho realizzato un sistema distribuito che simula 4 sportelli ATM che operano sullo stesso conto bancario.

Il problema da risolvere è che se due ATM modificassero il saldo nello stesso momento, il saldo finale sarebbe sbagliato. Per evitarlo ho usato l'algoritmo Token Ring per garantire la mutua esclusione: in ogni momento solo un ATM può modificare il saldo.

## Come funziona il sistema

I 4 nodi formano un anello logico:

```
ATM1 -> ATM2 -> ATM3 -> ATM4 -> ATM1
```

- Ogni ATM è un processo separato, avviato in un terminale diverso.
- Non c'è memoria condivisa: ogni nodo ha la sua memoria privata.
- I nodi comunicano solo tramite messaggi su localhost, con socket TCP. Ogni nodo conosce solo il suo successore.
- Nel sistema esiste un solo token, che circola continuamente lungo l'anello.
- Solo chi possiede il token può entrare nella sezione critica, cioè eseguire una transazione.
- Se un nodo non ha nessuna transazione da fare, inoltra subito il token al successore.
- Il saldo del conto viaggia dentro il token. Chi riceve il token legge il saldo, esegue la sua operazione, scrive il nuovo saldo nel token e lo passa avanti.

In questo modo le transazioni sono eseguite una alla volta, in ordine, e non possono mai sovrapporsi. Siccome il token continua a girare, tutti i nodi riescono prima o poi a eseguire la loro transazione.

## Transazioni previste

Il conto parte da un saldo iniziale di 1000 euro. Il token parte da ATM1.

| Nodo | Transazione | Saldo dopo l'operazione |
| --- | --- | --- |
| ATM1 | Nessuna transazione, inoltra il token | 1000 |
| ATM2 | Prelievo di 200 | 800 |
| ATM3 | Deposito di 100 | 900 |
| ATM4 | Prelievo di 500 | 400 |

Il saldo finale atteso è quindi 400 euro.

Ogni transazione viene eseguita in modo atomico e comprende la lettura del saldo dal token, il controllo che il prelievo sia possibile, l'aggiornamento del saldo, la scrittura del nuovo saldo nel token e la registrazione dell'operazione nei log.

## Struttura dei file

| File | Descrizione |
| --- | --- |
| atm_node.py | Codice del nodo ATM: server, client, gestione del token e logica della sezione critica |
| requirements.txt | Nessuna dipendenza esterna, viene usato solo Python standard |
| start_demo_windows.bat | Script per avviare velocemente i 4 nodi su Windows |
| start_demo.sh | Script per avviare velocemente i 4 nodi su Linux / macOS |
| README.md | Questo file |

## Come avviare il progetto

### Prerequisiti

- Python 3 installato
- Sistema operativo Windows, Linux o macOS
- 4 terminali separati
- Porte 5001-5004 libere su localhost

Non serve installare librerie aggiuntive e non serve compilare niente, il codice Python si avvia direttamente.

### Comandi

Aprire 4 terminali separati e avviare un nodo in ognuno. Per evitare attese lunghe conviene avviarli in ordine inverso, dal 4 all'1, oppure tutti subito uno dopo l'altro.

**Terminale 1 - ATM1 (possiede il token all'inizio, saldo iniziale 1000, nessuna transazione):**
```bash
python atm_node.py --id 1 --port 5001 --succ-port 5002 --initial-holder --initial-balance 1000
```

**Terminale 2 - ATM2 (prelievo di 200):**
```bash
python atm_node.py --id 2 --port 5002 --succ-port 5003 --transactions withdraw:200
```

**Terminale 3 - ATM3 (deposito di 100):**
```bash
python atm_node.py --id 3 --port 5003 --succ-port 5004 --transactions deposit:100
```

**Terminale 4 - ATM4 (prelievo di 500):**
```bash
python atm_node.py --id 4 --port 5004 --succ-port 5001 --transactions withdraw:500
```

Su Windows, se il comando `python` non viene riconosciuto, usare `py` al posto di `python`.

Ogni terminale corrisponde ad un solo ATM. Nei log ogni riga inizia con l'ora e con il nome del nodo, ad esempio `[ATM2]`, così si capisce subito quale terminale sta parlando.

### Esempio di esecuzione

Quando si avviano i 4 nodi, nei log si vede questa sequenza:

1. ATM1 possiede il token, non ha transazioni e lo inoltra a ATM2 (Saldo: 1000 euro).
2. ATM2 riceve il token, esegue il prelievo di 200 e lo inoltra a ATM3 (Saldo: 800 euro).
3. ATM3 riceve il token, esegue il deposito di 100 e lo inoltra a ATM4 (Saldo: 900 euro).
4. ATM4 riceve il token, esegue il prelievo di 500 e lo inoltra a ATM1 (Saldo: 400 euro).
5. Il token continua a circolare con saldo 400, senza altre transazioni.

Per fermare il sistema basta premere `Ctrl+C` in ogni terminale.

## Log

Ogni nodo registra nei log:
- Ricezione del token
- Inoltro del token al successore
- Inizio e fine della transazione
- Saldo aggiornato dopo ogni transazione

Dai log si vede chiaramente il movimento del token e che in ogni momento solo un nodo sta eseguendo una transazione.

## Video dimostrativo

Il video dimostrativo del funzionamento, disponibile nel repository, mostra i 4 nodi in esecuzione su 4 terminali separati, la circolazione del token e l'esecuzione delle transazioni con saldo finale 400 euro.
