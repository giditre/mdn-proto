#!/bin/bash

if ! [[ -f $1 ]] ; then
	echo "ERROR: $1 is not a valid file name."
	exit 1
fi

if ! [[ -x $1 ]] ; then
	chmod +x $1
fi

filename=$(basename -- "$1")

logfilename="${filename%.*}.log"

echo $filename $logfilename

bash $filename > $logfilename &2>1 & 
