#!/bin/bash
# Fetch challenge files (parquet only, plus tract-id csvs); verify byte counts.
mkdir -p data/raw/challenge && cd data/raw/challenge
B=https://data.source.coop/humane-intelligence
curl -sS "$B?list-type=2&prefix=bias-bounty-mapping-equity-challenge/&max-keys=1000" > listing.xml
python3 - <<'PY' > todo.tsv
import re
x=open('listing.xml').read()
for k,s in re.findall(r'<Key>([^<]+)</Key>.*?<Size>(\d+)</Size>',x):
    if 'bulk-downloads' in k or 'roads' in k or 'rail' in k or 'infrastructure' in k: continue
    if k.endswith('.csv') and 'geoids' not in k and 'sample-submission' not in k: continue
    if '/strata/national/' in k and not any(t in k for t in ['strata-tract-table.parquet','census-tract-table.parquet','svi-tract','tribal-tract-table','ruca']): continue
    print(k, s, sep='\t')
PY
while IFS=$'\t' read k s; do
  f=${k#bias-bounty-mapping-equity-challenge/}; mkdir -p "$(dirname "$f")"
  for i in 1 2 3 4; do
    [ -f "$f" ] && [ "$(stat -c%s "$f")" = "$s" ] && break
    curl -sS -C - -o "$f" "$B/$k" || sleep $((2**i))
  done
  [ "$(stat -c%s "$f")" = "$s" ] || echo "SIZE MISMATCH $f"
done < todo.tsv
echo DONE
