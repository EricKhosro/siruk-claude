# Pass 3: adversarial check of a zoovet/nemo match batch

Read `instructions3.md` (same folder) first. Its identity, kind and price rules apply unchanged.

You are given:
- a batch (`batches3/batch-NN.json`): our items;
- another agent's answers for that batch (`results3/match-NN.json`).

Be skeptical. Your job is to REFUTE wrong claims and FIND what was missed.

For every variant:
1. **Each shop the matcher marked found:** open the page yourself (`rival.py zoovet-page` / `nemo-page`). Check EVERY axis and today's price for our exact pack/option. Refute on any mismatch:
   - size or count;
   - flavour, texture or lifestage;
   - colour or weight band;
   - a multipack where we sell a single (or the reverse);
   - the bag where we sell per kg (or the reverse);
   - a wrong price.
2. **Each shop the matcher marked NOT found:** search it yourself. Use several spellings (English line name, Russian, Armenian words from the register / hafo row name, the size) and the brand's list. If the shop carries the exact item, report it.

Write YOUR OWN final answer for every variant to `results3/verify-NN.json`. Use the same shape as the match file, plus two fields per variant:
- `"verdict"`: `"agree"` (same shops found at the same prices) or `"disagree"`;
- `"reason"`.

Then reply with a single line: the file path, how many variants you disagree on, and their variant ids.
