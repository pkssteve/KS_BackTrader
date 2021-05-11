#!/bin/bash

COMM=0.001
CASH=100000
search_dir=`ls /Users/stevepark/PycharmProjects/KS_BackTrader/datas/STOCK/*.csv`
totalcash=0
totalgain=0

for file in ${search_dir}
do
    echo "file is "${file}
    totalcash=$((totalcash+CASH))
    finalcash=`btrun --csvformat btcsv --data "${file}" --strategy RSI_Simple.py \
    --timeframe minutes --compression 60 --cash 100000 --todate 2020-07-12 --commission 0.001 --nostdstats | grep Ending | cut -d " " -f 7`
    finalcash=`echo ${finalcash}`|bc
    echo "final cash : "${finalcash}
    diff=`echo ${finalcash}-${CASH}|bc`
    totalgain = `echo ${totalgain}+${diff}|bc`
done

finalProfit=`echo ${totalgain}+${totalcash}|bc`
# finalRatio=`echo ${finalProfit} ${totalcash}|awk '{printf "%.2f", $1/$2}'`
finalRatio=$((echo scale=2 ; echo ${finalProfit} / ${totalcash}) | bc)
finalRatio=`echo ${finalRatio} 100|awk '{printf "%d", $1*$2}'`
finalRatio=$((finalRatio-100))

echo "Total profit : "${finalProfit}
echo "Total cash : "${totalcash}
echo "Earnings rate "${finalRatio}"%"

temp="btrun --csvformat btcsv --data "./datas/STOCK/FORD.csv" --strategy RSI_Simple.py \
    --timeframe minutes --compression 60 --cash 100000 --todate 2020-04-12   --commission 0.001 --plot"