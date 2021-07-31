#!/bin/bash

COMM=0.001
CASH=100000
search_dir=`ls /Users/stevepark/PycharmProjects/KS_BackTrader/datas/KOSDAQ_1D_4/*.csv`
totalcash=0
totalgain=0

output=result_twentyten4.csv

echo "Code,Return" > ${output}

for file in ${search_dir}
do
    echo "file is "${file}
    filename=`basename ${file}`
    filename=`echo ${filename%%.*}`
    totalcash=$((totalcash+CASH))
    finalcash=`btrun --csvformat btcsv --data "${file}" --strategy ST_MA5.py \
    --timeframe days --compression 1 --cash ${CASH} --fromdate 2010-02-02 --todate 2020-07-12 --commission 0.001 --nostdstats | grep Ending | cut -d " " -f 7`
    finalcash=`echo ${finalcash}|bc`
    delta=`echo ${finalcash}-${CASH}|bc`
    profit=`echo "scale=2;${delta}/${CASH}*100"|bc`
    echo "final cash : "${finalcash}" Return(%) "${profit}
    diff=`echo ${finalcash}-${CASH}|bc`
    totalgain=`echo ${totalgain}+${diff}|bc`
    echo ${filename}","${profit} >> ${output}
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