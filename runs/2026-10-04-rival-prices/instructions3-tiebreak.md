# Pass 3: tie-break on disputed zoovet/nemo matches

Read `instructions3.md` (same folder) first. Its identity, kind and price rules apply unchanged.

For each variant id you are given, a matcher (`results3/match-NN.json`) and an independent verifier
(`results3/verify-NN.json`) disagree about zoovet and/or nemo. The item itself is in `batches3/batch-NN.json`.
You are the final check. Decide each shop on the evidence YOU see on the rival's page today. Neither earlier
answer is presumed right.

For every disputed variant and each shop (zoovet, nemo):
1. Read both earlier answers: URL, price and evidence.
2. Open every URL either of them claims: `python rival.py nemo-page <url>` / `zoovet-page <url>`. Check EVERY
   axis against our item: brand, line, size/count/weight, flavour, colour, size band, model / article number.
   Article numbers help: nemo search by our article code or EAN (`python rival.py nemo "<code>"`) often returns
   the exact page.
3. If both claim different pages, decide which (if either) is our exact item. If BOTH are our exact item at
   different prices, take the HIGHER price and name the other one in the evidence.
4. If you cannot confirm a claimed page on every axis, mark the shop found=false and give the reason.

**zoovet.am is refusing connections from this machine today (TCP timeout).** Do not wait on it. `rival.py zoovet`
searches today's saved zoovet lists (shops.json, captured earlier today: name, URL, price, stock). Decide zoovet
on those saved rows, and say "zoovet checked against today's saved list; page not reachable" in the evidence.

Write `results3/tiebreak-NN.json` (one file per batch you are given):
`{"results":[{"variant_id":…, "zoovet":{…}, "nemo":{…}, "confidence":"high|medium|low", "reason":"…"}]}`.
Use the same per-shop shape as the match files: found, url, price, old_price, name, in_stock, evidence.
Include ONLY the disputed variant ids you were given, and give an answer for BOTH shops for each of them.

Then reply with one line per file: its path, and for each variant the final zoovet/nemo price or "-".
