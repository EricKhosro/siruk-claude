---
name: translate-blog
description: Translate Siruk blog posts (siruk.am/blog) from English into Armenian and Russian, by meaning and not word for word, and write them into the admin with the post's title, summary, every text block and its SEO meta. Use when the user says there is a new blog post / article, asks to translate the blog or a post, or asks which posts still lack ru / hy.
argument-hint: [post id | "new" | "all"]
---

Translate blog posts into `ru` and `hy`. Which posts:

$ARGUMENTS

(Empty or "new" → every post that `status` shows as MISSING. A number → that post.
"all" → every post, but a post that already has its own ru/hy text is only
overwritten after the user says so.)

The script is `scripts/blog-translate.py` (status / export / check / apply). Files go
to `runs/<today>/blog/`. The English is never changed.

## The user's brief (2026-11-12): what a translation must be

1. **By meaning, not word for word.** Understand the idea and the intent, then write it
   as a native writer would. Restructure sentences, swap idioms for local ones, drop
   English rhythm ("Here is everything you need to know" → "Ниже всё, что действительно
   нужно знать" / "Ստորև այն ամենն է, ինչ իսկապես պետք է իմանալ").
2. **Natural and formal.** Clear, professional, easy to read, Siruk's warm voice kept.
   Address the reader as **вы** / **դուք** (lower-case вы).
3. **Each language pure.** No English or Russian words in Armenian, no English or
   Armenian words in Russian. Only proper names stay Latin: Siruk, brand names
   (Schesir, Purina…), named sources (PetMD, WSAVA, FEDIAF, Cornell → Корнелл / Քորնել
   when it reads as a name). Link labels pointing to English sources are translated
   ("Cornell: Feeding Your Cat" → "Корнелл: кормление кошки" / "Քորնել. կատվի կերակրումը").
4. **Little punctuation.** No exclamation marks. Replace English dashes with commas,
   colons or a new sentence. Russian keeps only a dash that grammar needs
   ("питомцы — это семья"). Armenian has none.
5. **Nothing added, nothing dropped.** Every paragraph, list item, table cell, number,
   source and caveat stays. Same HTML: same tags, the same links in the same places.

## Words: never these, use these

The user's hard rule: **no word that is also a curse or insult**, above all for
young animals.

| English | Armenian ✔ | Armenian ✘ | Russian ✔ | Russian ✘ |
|---|---|---|---|---|
| puppy / puppies | **քոթոթ, քոթոթներ** (the catalogue's lifestage value) | **լակոտ**, շան ձագ, շնաձագ (insults) | **щенок, щенки** (catalogue value, neutral) | — |
| kitten | **կատվի ձագ, ձագուկ** (catalogue: Կատվի ձագեր) | | **котёнок, котята** | |
| female dog | էգ շուն | | **самка, девочка** | **сука** |
| male dog | արու շուն | | **самец, мальчик** | **кобель** |
| animal | **կենդանի** | **անասուն** on its own (= "brute", an insult). Compounds are fine: անասնաբույժ, անասնաբուժական | **животное, питомец** | скотина, тварь |
| vet | **անասնաբույժ** | վետերինար (loanword) | **ветеринар** | ветеринарка |
| stool / poop | **կղանք**, ջրիկ կղանք | քաք | **стул**, кал | какашки, дерьмо |
| diarrhoea | **լուծ** | | **диарея**, жидкий стул | понос |
| vomiting | **փսխում** | | **рвота** | блевать |
| flatulence | **գազեր**, փքվածություն | | **газы**, газообразование | пукать |
| eat (animal) | **ուտել** | | **есть** | жрать |
| mouth / face | **բերան, դունչ** | | **мордочка** (warm) | морда (rude in a person-like text) |
| small dog size "toy" | **շատ փոքր** | գաճաճ | **карликовая** | той |
| treats | **հյուրասիրություններ** (category name) | լակոմություն | **лакомства** (category name) | |
| dewormer | **հակաճիճվային միջոց** (category) | | **антигельминтик**, средство от глистов | |
| flea & tick | **լվերի և տզերի դեմ** | | **от блох и клещей** | |
| bed | **պառկելատեղ** | | **лежак, лежанка** | |
| complete / complementary food | **լիարժեք / լրացուցիչ** կեր | | **полнорационный / дополнительный** корм | |
| pouch | **փաթեթիկ** | | **пакетик** | пауч |
| fur baby | **փափլիկ ընկեր** | | **пушистый малыш** | |

Armenian loanwords to avoid: կոնկրետ → տվյալ, սթրես → լարվածություն, նորմալ →
բնականոն, իդեալական → կատարյալ, ակտիվ → շարժուն, սեզոն → շրջան/եղանակ, ռադիատոր →
ջեռուցման մարտկոց, բակտերիա → մանրէ, ալկոհոլ → ոգելից խմիչք, պրեմիում → բարձրորակ,
ռիսկ → վտանգ, թերմոմետր → ջերմաչափ. Accepted as Armenian: վիտամին, կալորիա, սոուս,
ակվարիում, համստեր, միկրոչիպ, պաշտետ, chemical names (տաուրին, քսիլիտոլ).
Loose ends: "nuts" is ընկուզեղեն (ընդեղեն = legumes). Sweet cherry is կեռաս (բալ =
sour). Non-stick is չկպչող.

**Category and product words come from the live catalogue**, so the blog matches the
shop. Before a post with a new topic, read the names: `SIRUK_LANG=hy scripts/api.sh GET
"/categories?perPage=200"` (and `ru`), plus `reference/translations-attributes.json`
(lifestages, breed sizes).

Armenian food and place names, as Armenians write them: խորոված / хоровац, տոլմա /
толма, բաստուրմա, սուջուխ / суджух, չաման / чаман, մածուն / мацун, լոռի, չանախ,
լավաշ, օղի / оги, ջեզվե / джезве, ղափամա / гапама, սպաս / спас, Գումի շուկա /
рынок ГУМ.

## Armenian punctuation

- Full stop **։** (U+0589), never ":" or a Latin "." at the end of a sentence.
- Colon: the mijaket **.** (a Latin period, or ․ U+2024) or a rewrite, never ":".
  ("Վտանգները. ինչից պետք է խուսափել")
- Question mark **՞** on the stressed vowel of the question word ("Ինչո՞ւ", "Կարելի՞ է",
  "Որքա՞ն"), and the sentence still ends with ։ (a heading may end on the word).
- **՝** for an apposition or a pause ("օրինակ՝ տաուրինը", "Կատուն՝ ոչ").
- Numbers: 10%-ը, 7°C-ից, 5–10 կգ, թեյի գդալ / ճաշի գդալ.

## Steps

1. `account_status` / `scripts/api.sh GET /account` → 200 (on 401 re-capture the
   token, CLAUDE.md "Environments").
2. `python3 scripts/blog-translate.py status`: MISSING posts are the work list.
3. Per post: `python3 scripts/blog-translate.py export <id>`, then Read
   `runs/<today>/blog/p<id>-en.txt` in full (title, summary, meta, every block). If it
   says a locale **already has its own text**, show the user and ask before replacing it.
   A legacy `content` field → stop and ask.
4. Write the translation files in `runs/<today>/blog/tr/`:
   - `p<id>-ru.json` / `p<id>-hy.json`: `{"title", "featured_description"}`, plus
     `"meta": {"title" ≤ 60, "description" ≤ 160}` **only when en has meta**.
   - `p<id>-<lang>-b<blockId>.html`, one per **text** block. Keep every tag, `&nbsp;`
     spacer, table and link. Image and related-products blocks are passed through by the
     script, so don't write files for them.
   - **siruk.am links get the locale prefix**: `https://siruk.am/dog/…` →
     `https://siruk.am/ru/dog/…` / `https://siruk.am/hy/dog/…` (the storefront locales are
     en, ru, hy). External links stay as they are.
   - Write the whole text yourself, as a translator, not through a machine-translation
     call. Re-read each paragraph in the target language alone: does it sound written
     there?
5. `python3 scripts/blog-translate.py check <id>` until it prints "all checks pass". It
   catches banned words, wrong-script letters, Latin words that aren't names (add a
   real proper name to `LATIN_OK` in the script), "!", too many dashes, Latin ":" in
   Armenian, missing or extra links and tags, unlocalised siruk.am links, and meta
   length. The check is a floor, not the review: also read for the loanword list and
   the word table above.
6. `python3 scripts/blog-translate.py apply <id>` (dry run), then `apply <id> --apply`.
   The user asking for the translation is the go-ahead to write it. The script refuses
   when `check` fails, writes ru then hy one call at a time, reads each back and confirms
   that en (texts, dates, image, authors, meta) is unchanged. Report a failed read-back
   as a failure.
7. Tell the user: each post's ru / hy title, what the read-back showed, anything you left
   for them (an existing translation you didn't overwrite, a link you couldn't localise,
   a doubtful source), and anything odd you saw in the English (a duplicated block, a
   typo), with an offer to fix it. Never fix the English unasked.

## API facts (siruk-web `PostController`, checked 2026-11-12)

- `PUT /posts/<id>` with `"locale"` writes that locale's `title`, `featured_description`
  and each block's text. `slug`, category, authors, flags, dates and images are shared
  across languages.
- `content_blocks` is a **full sync**: a block left out of the PUT is deleted in every
  language. `author_ids` is synced the same way. The script always sends all of them.
- `vet_reviews[].review_text` is single-language (a pivot column). The script resends
  en's text. A post with a vet review keeps that review in English: tell the user.
- `meta` is stored only when the request carries it, and `meta_image` is synced at the
  same time. The script sends both, or neither.
- Leaving out `published_at` keeps the publish time. The admin GET gives only the date,
  so sending it back would move a post to midnight.
