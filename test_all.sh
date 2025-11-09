#!/bin/sh

for file in $(ls -1 *.json); do
   echo $file
   python drones_simu.py $file | tail -n 1 | sed "s/.*en \([^ ]*\) t.*/\1/g"
done
