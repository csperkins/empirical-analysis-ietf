#!/bin/sh

if [ $# = 0 ]; then
 echo "usage: bin/check-for-ack.sh <file> ..."
 exit 1
fi
 
for i in $*
do
  # Find instances of \section{Acknowledgements} that are not commented out:
  c=`egrep -c -i -n '^\\\\section.?\\{Acknowledgements' $i`
  if [ $c != 1 ]; then
    tput setaf 1 || true
    echo "WARNING: missing acknowledgements section?"
    tput sgr0    || true
  fi
done

