# S81_10_NATIVE_READ: the Arabic terms of data/fragrance_lexicon.json for the owner's native read

Moved out of the S81-10 PR body by the rebase round (RULINGS_REBASE_S81_10 RB10-8: the PR body stays
pure ASCII and under 25,600 bytes); the PR body keeps the transliteration / meaning / mark columns and
points here. Source: the GREEN PR body's table (the lexicon file is unchanged since the GREEN; its blob
at the rebased HEAD is git f1fad16d7e5410df83a88f82b2eda3ee42ec6d82).

## [NATIVE READ] the Arabic lexicon terms (data/fragrance_lexicon.json)
`needs_second_token` (GC-5): written in the file as a trailing ` *` on the term text (the frozen R06 schema keeps every term a plain string; `normalize` drops the mark): such a term never fires rule 1 alone; a second, different non-fragrance product-type token does. A house that is also an ordinary word can only add evidence (R-S10-4).

| group | transliteration (meaning) | Arabic | mark |
|---|---|---|---|
| concentrations | o de parfan (eau de parfum) | أو دو بارفان | - |
| concentrations | o de twalet (eau de toilette) | أو دو تواليت | - |
| concentrations | barfan (parfum) | بارفان | - |
| forms | itr (perfume) | عطر | - |
| forms | utur (perfumes) | عطور | - |
| forms | kolonya (cologne) | كولونيا | - |
| forms | dihn al oud (oud oil) | دهن العود | - |
| forms | bakhakh jism (body spray) | بخاخ جسم | - |
| forms | mu'attar sha'r (hair perfume) | معطر شعر | - |
| houses | shanel (Chanel) | شانيل | - |
| houses | diyor (Dior) | ديور | - |
| houses | lattafa | لطافة | - |
| houses | armaf | أرماف | - |
| houses | ajmal (also 'most beautiful': can only ADD evidence, GC-5) | أجمل | - |
| houses | al rasasi | الرصاصي | - |
| houses | al arabiya lil oud (Arabian Oud) | العربية للعود | - |
| houses | abdulsamad al qurashi | عبدالصمد القرشي | - |
| houses | al haramain | الحرمين | - |
| houses | amwaj (Amouage) | أمواج | - |
| notes | oud | عود | - |
| notes | misk (musk) | مسك | - |
| notes | anbar (amber) | عنبر | - |
| notes | ward (rose) | ورد | - |
| notes | yasmin (jasmine) | ياسمين | - |
| notes | sandal (sandalwood) | صندل | - |
| notes | zafaran (saffron) | زعفران | - |
| electronics | jawwal (mobile) | جوال | - |
| electronics | hatif (phone) | هاتف | - |
| electronics | labtob (laptop) | لابتوب | - |
| grocery | taam (food) | طعام | - |
| grocery | mashrub (beverage) | مشروب | - |
| grocery | munazzif (detergent) | منظف | - |
| supplements | fitamin (vitamin) | فيتامين | - |
| supplements | mukammil ghidhai (dietary supplement) | مكمل غذائي | - |
| makeup | mikyaj (makeup) | مكياج | - |
| makeup | ahmar shifah (lipstick) | أحمر شفاه | - |
| skincare | krim (cream; also a given name) | كريم | needs_second_token |
| skincare | lushan (lotion) | لوشن | - |
| haircare | shambu (shampoo) | شامبو | - |
| haircare | balsam (conditioner; also 'balm') | بلسم | needs_second_token |
| fashion | haqiba (bag) | حقيبة | - |
| fashion | hidha (shoe) | حذاء | - |
| fashion | saa (watch; also 'hour') | ساعة | needs_second_token |
