#!/bin/bash

[ $# -ne 1 ] && echo "Error: provide valid filename." && exit 1

[[ -f $1 ]] && echo "Error: file $1 already exists." && exit 1

vim /tmp/$1
cat /tmp/$1 | sed -e 's/\[$i\]/\[${i#0}\]/g; s/\[$j\]/\[${j#0}\]/g; s/\"$i\"/\"${i#0}\"/g; s/\"$j\"/\"${j#0}\"/g; s/\ $i\ /\ ${i#0}\ /g; s/\ $j\ /\ ${j#0}\ /g' > $1
rm /tmp/$1
chmod +x $1

