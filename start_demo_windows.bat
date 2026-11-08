@echo off
echo Avvio 4 nodi ATM in finestre separate (Windows)
start "ATM4 - 5004->5001" cmd /k python atm_node.py --id 4 --port 5004 --succ-port 5001 --transactions withdraw:500
timeout /t 1
start "ATM3 - 5003->5004" cmd /k python atm_node.py --id 3 --port 5003 --succ-port 5004 --transactions deposit:100
timeout /t 1
start "ATM2 - 5002->5003" cmd /k python atm_node.py --id 2 --port 5002 --succ-port 5003 --transactions withdraw:200
timeout /t 1
start "ATM1 - 5001->5002 INITIAL HOLDER" cmd /k python atm_node.py --id 1 --port 5001 --succ-port 5002 --initial-holder --initial-balance 1000
echo Tutti i nodi avviati in finestre separate. Controlla le 4 finestre.
