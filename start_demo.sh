#!/bin/bash
echo "Avvio demo Progetto 1 - Token Ring - 4 ATM su localhost"
echo "Assicurati di avere 4 terminali separati. Questo script avvia tutto in background per test rapido."
echo ""

# Avvio in background con log separati
python3 atm_node.py --id 4 --port 5004 --succ-port 5001 --transactions withdraw:500 > atm4.log 2>&1 &
sleep 0.5
python3 atm_node.py --id 3 --port 5003 --succ-port 5004 --transactions deposit:100 > atm3.log 2>&1 &
sleep 0.5
python3 atm_node.py --id 2 --port 5002 --succ-port 5003 --transactions withdraw:200 > atm2.log 2>&1 &
sleep 0.5
python3 atm_node.py --id 1 --port 5001 --succ-port 5002 --initial-holder --initial-balance 1000 > atm1.log 2>&1 &

echo "Nodi avviati in background. PID:"
jobs
echo ""
echo "Attendi 15 secondi poi controlla i log..."
sleep 15
echo "=== ATM1 ==="; cat atm1.log
echo "=== ATM2 ==="; cat atm2.log
echo "=== ATM3 ==="; cat atm3.log
echo "=== ATM4 ==="; cat atm4.log
echo ""
echo "Per terminare: pkill -f atm_node.py"
