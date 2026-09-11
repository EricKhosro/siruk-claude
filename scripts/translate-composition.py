#!/usr/bin/env python3
"""Rule-based ru/hy translation of composition / analytical-constituent /
additive lines (Trixie and Monge product pages), term by term.

The lines are formulaic ("Composition: chicken meat (58 %), rawhide, potato
starch … Store in a cool and dry place." / "Analytical constituents: Fat
content 5.0 %, Protein 18.0 % …" / "Additives: Vit. E 2000"). Each line is
tokenised on separators (", ", " (", ") ", ": ", "|", ";") and every term is
looked up in TERMS, longest phrase first; numbers, %, units and brand words
pass through. A term with no entry stays English and is reported, so nothing
is invented silently.

    scripts/translate-composition.py --check strings.json   # report unknown terms
    python3 -c "from translate_composition import tr; tr('…', 'ru')"
"""
import json, re, sys

TERMS = {
    # labels
    "composition": ("Состав", "Բաղադրություն"), "analytical constituents": ("Аналитические составляющие", "Անալիտիկ բաղադրիչներ"),
    "additives": ("Добавки", "Հավելումներ"), "nutritional additives": ("Питательные добавки", "Սննդային հավելումներ"),
    "store in a cool and dry place": ("Хранить в сухом прохладном месте", "Պահել զով և չոր տեղում"),
    "gluten-free formula": ("безглютеновая формула", "առանց գլյուտենի բաղադրություն"), "no added sugar": ("без добавленного сахара", "առանց ավելացված շաքարի"),
    "vegan": ("веганское", "վեգան"), "vegetarian": ("вегетарианское", "բուսակերական"), "without cocoa": ("без какао", "առանց կակաոյի"),
    "with omega 3 and omega 6 fatty acids": ("с жирными кислотами Омега-3 и Омега-6", "Օմեգա-3 և Օմեգա-6 ճարպաթթուներով"),
    "freeze-dried": ("сублимированная", "սառեցմամբ չորացրած"), "dried": ("сушёная", "չորացրած"), "fresh": ("свежий", "թարմ"), "dehydrated": ("дегидрированный", "ջրազրկված"),
    "thereof": ("из них", "որից"), "therof": ("из них", "որից"), "of which": ("из них", "որից"), "of these": ("из них", "որից"), "incl.": ("вкл.", "ներառյալ"), "including": ("включая", "ներառյալ"),
    "equal to": ("что равно", "հավասար է"), "purely vegetable": ("чисто растительные", "զուտ բուսական"),
    # analytical labels
    "fat content": ("Жиры", "Ճարպեր"), "crude fat": ("Сырой жир", "Հում ճարպ"), "moisture content": ("Влага", "Խոնավություն"), "moisture": ("Влага", "Խոնավություն"),
    "protein": ("Белок", "Սպիտակուց"), "crude protein": ("Сырой белок", "Հում սպիտակուց"), "crude ash": ("Сырая зола", "Հում մոխիր"), "crude fibre": ("Сырая клетчатка", "Հում բջջանյութ"),
    "crude fiber": ("Сырая клетчатка", "Հում բջջանյութ"), "crude fibres": ("Сырая клетчатка", "Հում բջջանյութ"), "ash": ("Зола", "Մոխիր"), "calcium": ("Кальций", "Կալցիում"), "phosphorus": ("Фосфор", "Ֆոսֆոր"),
    "omega-3 fatty acids": ("жирные кислоты Омега-3", "Օմեգա-3 ճարպաթթուներ"), "omega-6 fatty acids": ("жирные кислоты Омега-6", "Օմեգա-6 ճարպաթթուներ"),
    "omega 3": ("Омега-3", "Օմեգա-3"), "omega 6": ("Омега-6", "Օմեգա-6"), "energy": ("Энергия", "Էներգիա"), "sodium": ("Натрий", "Նատրիում"), "magnesium": ("Магний", "Մագնեզիում"),
    "potassium": ("Калий", "Կալիում"), "taurine": ("таурин", "տաուրին"), "starch": ("крахмал", "օսլա"), "nfe": ("БЭВ", "ԱԷՆ"), "sugar": ("сахар", "շաքար"), "sugars": ("сахара", "շաքարներ"),
    # additives / vitamins
    "vit-a": ("Вит. A", "Վիտ. A"), "vit-d3": ("Вит. D3", "Վիտ. D3"), "vit-d": ("Вит. D", "Վիտ. D"), "vit-e": ("Вит. E", "Վիտ. E"), "vit-c": ("Вит. C", "Վիտ. C"), "vit-k3": ("Вит. K3", "Վիտ. K3"),
    "vit-b1": ("Вит. B1", "Վիտ. B1"), "vit-b2": ("Вит. B2", "Վիտ. B2"), "vit-b6": ("Вит. B6", "Վիտ. B6"), "vit-b12": ("Вит. B12", "Վիտ. B12"), "vit-k": ("Вит. K", "Վիտ. K"), "vit-b": ("Вит. B", "Վիտ. B"),
    "pork belly with beechwood smoke": ("свиная грудинка букового копчения", "խոզի փորամիս հաճարենու ծխով"), "pork belly": ("свиная грудинка", "խոզի փորամիս"),
    "vitamin a": ("Витамин A", "Վիտամին A"), "vitamin d3": ("Витамин D3", "Վիտամին D3"), "vitamin e": ("Витамин E", "Վիտամին E"), "vitamin c": ("Витамин C", "Վիտամին C"),
    "vitamin b1": ("Витамин B1", "Վիտամին B1"), "vitamin b2": ("Витамин B2", "Վիտամին B2"), "vitamin b6": ("Витамин B6", "Վիտամին B6"), "vitamin b12": ("Витамин B12", "Վիտամին B12"),
    "biotin": ("Биотин", "Բիոտին"), "niacinamide": ("Ниацинамид", "Նիացինամիդ"), "niacin": ("Ниацин", "Նիացին"), "nicotinic acid": ("Никотиновая кислота", "Նիկոտինաթթու"),
    "calcium-d-pantothenat": ("Кальций-D-пантотенат", "Կալցիում-D-պանտոթենատ"), "calcium-d-pantothenate": ("Кальций-D-пантотенат", "Կալցիում-D-պանտոթենատ"), "pantothenic acid": ("Пантотеновая кислота", "Պանտոթենաթթու"),
    "folic acid": ("Фолиевая кислота", "Ֆոլաթթու"), "choline chloride": ("Хлорид холина", "Խոլին քլորիդ"), "chocolate flavouring": ("Шоколадный ароматизатор", "Շոկոլադի բուրավետիչ"),
    "copper": ("Медь", "Պղինձ"), "zinc": ("Цинк", "Ցինկ"), "iron": ("Железо", "Երկաթ"), "manganese": ("Марганец", "Մանգան"), "iodine": ("Йод", "Յոդ"), "selenium": ("Селен", "Սելեն"),
    "retinyl acetate": ("ретинилацетат", "ռետինիլացետատ"), "all-rac-alpha-tocopheryl acetate": ("all-rac-альфа-токоферилацетат", "all-rac-ալֆա-տոկոֆերիլացետատ"),
    "all-rac-alpha-tocopheryl-acetate": ("all-rac-альфа-токоферилацетат", "all-rac-ալֆա-տոկոֆերիլացետատ"), "sodium selenite": ("селенит натрия", "նատրիումի սելենիտ"),
    "manganous sulphate monohydrate": ("сульфат марганца моногидрат", "մանգանի սուլֆատ մոնոհիդրատ"), "zinc oxide": ("оксид цинка", "ցինկի օքսիդ"), "zinc sulphate monohydrate": ("сульфат цинка моногидрат", "ցինկի սուլֆատ մոնոհիդրատ"),
    "copper (ii) sulphate pentahydrate": ("сульфат меди (II) пентагидрат", "պղնձի (II) սուլֆատ պենտահիդրատ"), "iron (ii) sulphate monohydrate": ("сульфат железа (II) моногидрат", "երկաթի (II) սուլֆատ մոնոհիդրատ"),
    "calcium iodate anhydrous": ("йодат кальция безводный", "կալցիումի յոդատ անջուր"), "iu": ("МЕ", "ՄՄ"), "iu/kg": ("МЕ/кг", "ՄՄ/կգ"), "mg/kg": ("мг/кг", "մգ/կգ"), "mg": ("мг", "մգ"), "g/kg": ("г/кг", "գ/կգ"),
    "l-carnitine": ("L-карнитин", "L-կարնիտին"), "glucosamine": ("глюкозамин", "գլյուկոզամին"), "chondroitin sulphate": ("хондроитинсульфат", "խոնդրոիտին սուլֆատ"),
    "xylo-oligosaccharide": ("ксилоолигосахарид", "քսիլո-օլիգոսախարիդ"), "xylo-oligosaccharides": ("ксилоолигосахариды", "քսիլո-օլիգոսախարիդներ"), "xos": ("XOS", "XOS"),
    "yucca schidigera": ("юкка Шидигера", "յուկկա Շիդիգերա"), "spirulina": ("спирулина", "սպիրուլինա"), "spirulina algae": ("водоросль спирулина", "սպիրուլինա ջրիմուռ"),
    "instructions for use": ("Инструкция по применению", "Օգտագործման հրահանգներ"),
    # ingredients
    "meat and animal derivatives": ("мясо и продукты животного происхождения", "միս և կենդանական ծագման մթերքներ"), "meat and animal derivates": ("мясо и продукты животного происхождения", "միս և կենդանական ծագման մթերքներ"),
    "meat and animal by-products": ("мясо и мясные субпродукты", "միս և կենդանական ենթամթերքներ"), "meats and derivatives": ("мясо и продукты животного происхождения", "միս և կենդանական ծագման մթերքներ"),
    "meat and derivatives": ("мясо и продукты животного происхождения", "միս և կենդանական ծագման մթերքներ"), "fish and fish derivatives": ("рыба и рыбные продукты", "ձուկ և ձկնային մթերքներ"),
    "fish and fish derivates": ("рыба и рыбные продукты", "ձուկ և ձկնային մթերքներ"), "fish and fish by-products": ("рыба и рыбные субпродукты", "ձուկ և ձկնային ենթամթերքներ"),
    "cereals": ("злаки", "հացահատիկ"), "derivatives of vegetable origin": ("продукты растительного происхождения", "բուսական ծագման մթերքներ"), "vegetable derivatives": ("продукты растительного происхождения", "բուսական ծագման մթերքներ"),
    "vegetable protein extracts": ("растительные белковые экстракты", "բուսական սպիտակուցի էքստրակտներ"), "vegetables": ("овощи", "բանջարեղեն"), "vegetable": ("растительный", "բուսական"),
    "oils and fats": ("масла и жиры", "յուղեր և ճարպեր"), "minerals": ("минералы", "հանքանյութեր"), "mineral substances": ("минеральные вещества", "հանքային նյութեր"), "milk and milk derivatives": ("молоко и молочные продукты", "կաթ և կաթնամթերք"),
    "propylene glycol": ("пропиленгликоль", "պրոպիլենգլիկոլ"), "glycerine": ("глицерин", "գլիցերին"), "glycerol": ("глицерин", "գլիցերին"), "sorbitol": ("сорбит", "սորբիտ"), "trehalose": ("трегалоза", "տրեհալոզա"), "sucrose": ("сахароза", "սախարոզ"),
    "maltodextrin": ("мальтодекстрин", "մալտոդեքստրին"), "cellulose": ("целлюлоза", "ցելյուլոզ"), "collagen": ("коллаген", "կոլագեն"), "rawhide": ("сыромятная кожа", "հում կաշի"), "yeast": ("дрожжи", "խմորիչ"), "yeasts": ("дрожжи", "խմորիչներ"),
    "tapioca starch": ("крахмал тапиоки", "տապիոկայի օսլա"), "potato starch": ("картофельный крахмал", "կարտոֆիլի օսլա"), "corn starch": ("кукурузный крахмал", "եգիպտացորենի օսլա"), "wheat starch": ("пшеничный крахмал", "ցորենի օսլա"), "pea starch": ("гороховый крахмал", "ոլոռի օսլա"),
    "rice flour": ("рисовая мука", "բրնձի ալյուր"), "wheat flour": ("пшеничная мука", "ցորենի ալյուր"), "oat flour": ("овсяная мука", "վարսակի ալյուր"), "corn flour": ("кукурузная мука", "եգիպտացորենի ալյուր"), "flour": ("мука", "ալյուր"),
    "soybean protein": ("соевый белок", "սոյայի սպիտակուց"), "pea protein": ("гороховый белок", "ոլոռի սպիտակուց"), "milk protein": ("молочный белок", "կաթնային սպիտակուց"), "plant protein": ("растительный белок", "բուսական սպիտակուց"),
    "hydrolysed animal protein": ("гидролизованный животный белок", "հիդրոլիզացված կենդանական սպիտակուց"), "hydrolysed animal proteins": ("гидролизованные животные белки", "հիդրոլիզացված կենդանական սպիտակուցներ"),
    "chicken": ("курица", "հավ"), "chicken meat": ("куриное мясо", "հավի միս"), "chicken breast": ("куриная грудка", "հավի կրծքամիս"), "chicken liver": ("куриная печень", "հավի լյարդ"), "chicken hearts": ("куриные сердечки", "հավի սրտիկներ"),
    "chicken oil": ("куриный жир", "հավի յուղ"), "chicken fat": ("куриный жир", "հավի ճարպ"), "animal fat": ("животный жир", "կենդանական ճարպ"), "poultry": ("птица", "թռչնամիս"), "poultry meat": ("мясо птицы", "թռչնամիս"),
    "turkey": ("индейка", "հնդկահավ"), "turkey meat": ("мясо индейки", "հնդկահավի միս"), "duck": ("утка", "բադ"), "duck meat": ("утиное мясо", "բադի միս"), "duck breast": ("утиная грудка", "բադի կրծքամիս"),
    "beef": ("говядина", "տավարի միս"), "beef skin": ("говяжья кожа", "տավարի կաշի"), "veal": ("телятина", "հորթի միս"), "lamb": ("ягнёнок", "գառ"), "lamb meat": ("мясо ягнёнка", "գառան միս"), "lamb liver": ("печень ягнёнка", "գառան լյարդ"),
    "pork": ("свинина", "խոզի միս"), "pork meat": ("свинина", "խոզի միս"), "pork liver": ("свиная печень", "խոզի լյարդ"), "liver": ("печень", "լյարդ"), "rabbit": ("кролик", "ճագար"), "rabbit meat": ("мясо кролика", "ճագարի միս"),
    "rabbit legs with fur": ("кроличьи лапки с шерстью", "ճագարի թաթիկներ մորթով"), "rabbit tails with fur": ("кроличьи хвостики с шерстью", "ճագարի պոչիկներ մորթով"), "hare": ("заяц", "նապաստակ"), "hare meat": ("мясо зайца", "նապաստակի միս"),
    "venison": ("оленина", "եղնիկի միս"), "deer": ("олень", "եղնիկ"), "buffalo": ("буйвол", "գոմեշ"), "buffalo meat": ("мясо буйвола", "գոմեշի միս"), "horse": ("конина", "ձիու միս"), "horse meat": ("конина", "ձիու միս"),
    "boar": ("кабан", "վարազ"), "wild boar": ("кабан", "վայրի վարազ"), "game": ("дичь", "որսամիս"), "tripe": ("рубец", "ստամոքս"), "rumen": ("рубец", "ստամոքս"), "egg yolk powder": ("порошок яичного желтка", "ձվի դեղնուցի փոշի"),
    "eggs": ("яйца", "ձու"), "egg": ("яйцо", "ձու"), "cheese": ("сыр", "պանիր"), "milk": ("молоко", "կաթ"),
    "fish": ("рыба", "ձուկ"), "whitefish": ("белая рыба", "սպիտակ ձուկ"), "white fish": ("белая рыба", "սպիտակ ձուկ"), "white fish skin": ("кожа белой рыбы", "սպիտակ ձկան մաշկ"), "whitefish skin": ("кожа белой рыбы", "սպիտակ ձկան մաշկ"),
    "salmon": ("лосось", "սաղմոն"), "salmon skin": ("кожа лосося", "սաղմոնի մաշկ"), "salmon oil": ("лососевое масло", "սաղմոնի յուղ"), "fish oil": ("рыбий жир", "ձկան յուղ"), "cod": ("треска", "ձողաձուկ"), "codfish": ("треска", "ձողաձուկ"),
    "tuna": ("тунец", "թունա"), "trout": ("форель", "իշխան"), "herring": ("сельдь", "տառեխ"), "anchovies": ("анчоусы", "անչոուս"), "shrimps": ("креветки", "ծովախեցգետին"), "shrimp": ("креветка", "ծովախեցգետին"), "prawns": ("креветки", "ծովախեցգետին"),
    "squid powder": ("порошок кальмара", "կաղամարի փոշի"), "pollock": ("минтай", "մինտայ"),
    "rice": ("рис", "բրինձ"), "maize": ("кукуруза", "եգիպտացորեն"), "corn": ("кукуруза", "եգիպտացորեն"), "wheat": ("пшеница", "ցորեն"), "oats": ("овёс", "վարսակ"), "barley": ("ячмень", "գարի"), "peas": ("горох", "ոլոռ"), "lupin meal": ("люпиновая мука", "լյուպինի ալյուր"),
    "potato": ("картофель", "կարտոֆիլ"), "potatoes": ("картофель", "կարտոֆիլ"), "sweet potato": ("батат", "բաթաթ"), "carrots": ("морковь", "գազար"), "carrot": ("морковь", "գազար"), "fresh carrots": ("свежая морковь", "թարմ գազար"),
    "green beans": ("стручковая фасоль", "կանաչ լոբի"), "dried green beans": ("сушёная стручковая фасоль", "չորացրած կանաչ լոբի"), "fresh green beans": ("свежая стручковая фасоль", "թարմ կանաչ լոբի"), "dried tomato pomace": ("сушёный томатный жмых", "չորացրած լոլիկի քուսպ"),
    "banana": ("банан", "բանան"), "apple": ("яблоко", "խնձոր"), "pear": ("груша", "տանձ"), "pineapple": ("ананас", "արքայախնձոր"), "orange": ("апельсин", "նարինջ"), "raspberries": ("малина", "ազնվամորի"), "citrus fruits": ("цитрусовые", "ցիտրուսներ"),
    "cranberries": ("клюква", "լոռամիրգ"), "blueberries": ("черника", "հապալաս"), "pomegranate": ("гранат", "նուռ"), "plum": ("слива", "սալոր"), "chestnuts": ("каштаны", "շագանակ"), "rosehips": ("шиповник", "մասուր"),
    "parsley": ("петрушка", "մաղադանոս"), "thyme": ("тимьян", "ուրց"), "rosemary": ("розмарин", "խնկունի"), "sage": ("шалфей", "եղեսպակ"), "chamomile": ("ромашка", "երիցուկ"), "lemon balm": ("мелисса", "մեղրախոտ"), "peppermint": ("мята перечная", "պղպեղնանուխ"),
    "mint": ("мята", "անանուխ"), "catnip": ("кошачья мята", "կատվախոտ"), "aloe vera": ("алоэ вера", "ալոե վերա"), "artichoke": ("артишок", "կանկար"), "turmeric": ("куркума", "քրքում"), "bell pepper powder": ("порошок сладкого перца", "քաղցր պղպեղի փոշի"),
    "flaxseed oil": ("льняное масло", "կտավատի յուղ"), "linseed": ("льняное семя", "կտավատի սերմ"), "sesame": ("кунжут", "քունջութ"), "beet pulp": ("свекольный жом", "ճակնդեղի քուսպ"), "dried beet pulp": ("сушёный свекольный жом", "չորացրած ճակնդեղի քուսպ"),
    "brewer's yeast": ("пивные дрожжи", "գարեջրի խմորիչ"),
    "buffalo headskin": ("кожа головы буйвола", "գոմեշի գլխի կաշի"), "buffalo skin": ("кожа буйвола", "գոմեշի կաշի"), "horsemeat": ("конина", "ձիու միս"), "malt": ("солод", "ածիկ"),
    "rabbit ears": ("кроличьи уши", "ճագարի ականջներ"), "vegetable oil": ("растительное масло", "բուսական յուղ"), "pea flour": ("гороховая мука", "ոլոռի ալյուր"), "pea fibre": ("гороховая клетчатка", "ոլոռի բջջանյութ"),
    "alaska pollock": ("минтай", "մինտայ"), "baking soda": ("пищевая сода", "խմորի սոդա"), "carob meal": ("мука рожкового дерева", "եղջերենու ալյուր"), "chitosan": ("хитозан", "խիտոզան"),
    "molluscs and crustaceans": ("моллюски и ракообразные", "փափկամարմիններ և խեցգետնակերպեր"), "prawn": ("креветка", "ծովախեցգետին"), "pork belly with beechwood smoke": ("свиная грудинка буковогo копчения", "խոզի փորամիս հաճարենու ծխով"),
    "peanut protein": ("арахисовый белок", "գետնանուշի սպիտակուց"), "soybean oil": ("соевое масло", "սոյայի յուղ"), "steam-cooked": ("приготовлено на пару", "գոլորշով եփած"), "chicken meat/lamb meat/beef meat": ("куриное мясо/мясо ягнёнка/говядина", "հավի միս/գառան միս/տավարի միս"),
    "dl-methionine": ("DL-метионин", "DL-մեթիոնին"), "dl-methionine technically pure": ("DL-метионин технически чистый", "DL-մեթիոնին տեխնիկապես մաքուր"), "antioxidants": ("антиоксиданты", "հակաօքսիդանտներ"),
    "technological additives": ("Технологические добавки", "Տեխնոլոգիական հավելումներ"), "sensory additives": ("Сенсорные добавки", "Զգայական հավելումներ"), "zootechnical additives": ("Зоотехнические добавки", "Զոոտեխնիկական հավելումներ"),
    "nutritional additives/kg": ("Питательные добавки/кг", "Սննդային հավելումներ/կգ"), "nutritionaladditives/kg": ("Питательные добавки/кг", "Սննդային հավելումներ/կգ"), "metabolisable energy": ("Обменная энергия", "Փոխանակային էներգիա"),
    "metabolizable energy": ("Обменная энергия", "Փոխանակային էներգիա"), "metabolized energy": ("Обменная энергия", "Փոխանակային էներգիա"), "atwater calculation": ("расчёт по Этуотеру", "Էթուոթերի հաշվարկ"),
    "urine acidifying substance": ("вещество, подкисляющее мочу", "մեզը թթվեցնող նյութ"), "urine alkalising substance": ("вещество, подщелачивающее мочу", "մեզը հիմնայնացնող նյութ"), "calcium/phosphorus ratio": ("соотношение кальций/фосфор", "կալցիում/ֆոսֆոր հարաբերակցություն"),
    "kcal/kg": ("ккал/кг", "կկալ/կգ"), "kcal": ("ккал", "կկալ"), "crude fats": ("Сырые жиры", "Հում ճարպեր"), "dehydrated meat": ("дегидрированное мясо", "ջրազրկված միս"), "dried meat": ("сушёное мясо", "չորացրած միս"),
    "dehydrated chicken": ("дегидрированная курица", "ջրազրկված հավ"), "dehydrated salmon": ("дегидрированный лосось", "ջրազրկված սաղմոն"), "dried salmon": ("сушёный лосось", "չորացրած սաղմոն"), "fresh salmon": ("свежий лосось", "թարմ սաղմոն"),
    "fresh chicken": ("свежая курица", "թարմ հավ"), "fresh meat": ("свежее мясо", "թարմ միս"), "chicken protein": ("куриный белок", "հավի սպիտակուց"), "salmon protein": ("белок лосося", "սաղմոնի սպիտակուց"),
    "highly digestible ingredients": ("легкоусвояемые ингредиенты", "հեշտ մարսվող բաղադրիչներ"), "protein sources": ("источники белка", "սպիտակուցի աղբյուրներ"), "selected protein source": ("отборный источник белка", "ընտիր սպիտակուցի աղբյուր"),
    "carbohydrate source": ("источник углеводов", "ածխաջրերի աղբյուր"), "lentils": ("чечевица", "ոսպ"), "pumpkin": ("тыква", "դդում"), "zucchini": ("цукини", "ցուկինի"), "courgette": ("цукини", "ցուկինի"),
    "beans": ("фасоль", "լոբի"), "tomato": ("томат", "լոլիկ"), "rose hip": ("шиповник", "մասուր"), "rosehip": ("шиповник", "մասուր"), "mos": ("MOS", "MOS"), "mannan-oligosaccharides": ("маннанолигосахариды", "մանան-օլիգոսախարիդներ"),
    "fructo-oligosaccharides": ("фруктоолигосахариды", "ֆրուկտո-օլիգոսախարիդներ"), "fos": ("FOS", "FOS"), "inulin": ("инулин", "ինուլին"), "glucosamine hydrochloride": ("глюкозамина гидрохлорид", "գլյուկոզամինի հիդրոքլորիդ"),
    "chondroitin": ("хондроитин", "խոնդրոիտին"), "green tea extract": ("экстракт зелёного чая", "կանաչ թեյի էքստրակտ"), "rosemary extract": ("экстракт розмарина", "խնկունու էքստրակտ"), "vitamins": ("витамины", "վիտամիններ"),
    "trace elements": ("микроэлементы", "միկրոտարրեր"), "amino acids": ("аминокислоты", "ամինաթթուներ"), "l-lysine": ("L-лизин", "L-լիզին"), "methionine": ("метионин", "մեթիոնին"), "lysine": ("лизин", "լիզին"),
    "sodium chloride": ("хлорид натрия", "նատրիումի քլորիդ"), "potassium chloride": ("хлорид калия", "կալիումի քլորիդ"), "calcium carbonate": ("карбонат кальция", "կալցիումի կարբոնատ"), "dicalcium phosphate": ("дикальцийфосфат", "դիկալցիումի ֆոսֆատ"),
    "monosodium phosphate": ("монофосфат натрия", "նատրիումի մոնոֆոսֆատ"), "sodium tripolyphosphate": ("триполифосфат натрия", "նատրիումի տրիպոլիֆոսֆատ"), "cassia gum": ("камедь кассии", "կասիայի մաստակ"), "guar gum": ("гуаровая камедь", "գուարի մաստակ"),
    "carrageenan": ("каррагинан", "կարագինան"), "xanthan gum": ("ксантановая камедь", "քսանթանի մաստակ"), "tapioca": ("тапиока", "տապիոկա"), "wheat gluten": ("пшеничный глютен", "ցորենի սնձան"), "corn gluten": ("кукурузный глютен", "եգիպտացորենի սնձան"),
    "eggs and chicken liver with a digestibility higher than 85%.": ("яйца и куриная печень с усвояемостью выше 85 %.", "ձու և հավի լյարդ 85 %-ից բարձր մարսելիությամբ։"),
    "chicken (dehydrated": ("курица (дегидрированная", "հավ (ջրազրկված"), "ox liver": ("говяжья печень", "տավարի լյարդ"), "beef liver": ("говяжья печень", "տավարի լյարդ"), "hydrolysed animal proteins": ("гидролизованные животные белки", "հիդրոլիզացված կենդանական սպիտակուցներ"),
    "animal fats": ("животные жиры", "կենդանական ճարպեր"), "fish meal": ("рыбная мука", "ձկան ալյուր"), "poultry fat": ("жир птицы", "թռչնի ճարպ"), "dried whole eggs": ("сушёные цельные яйца", "չորացրած ամբողջական ձու"),
    "psyllium": ("псиллиум", "պսիլիում"), "salt": ("соль", "աղ"), "sugar beet pulp": ("свекловичный жом", "շաքարի ճակնդեղի քուսպ"), "spirulina powder": ("порошок спирулины", "սպիրուլինայի փոշի"),
    "yucca schidigera extract": ("экстракт юкки Шидигера", "յուկկա Շիդիգերայի էքստրակտ"), "fresh chicken meat": ("свежее куриное мясо", "թարմ հավի միս"), "chicken and turkey": ("курица и индейка", "հավ և հնդկահավ"),
    "3 to 8 weeks": ("от 3 до 8 недель", "3-ից 8 շաբաթ"), "weeks": ("недель", "շաբաթ"), "months": ("месяцев", "ամիս"), "and": ("и", "և"), "betaglucans": ("бета-глюканы", "բետա-գլյուկաններ"), "milk powder": ("сухое молоко", "կաթի փոշի"),
}
import os as _os
_extra = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "reference", "translations-composition.json")
if _os.path.exists(_extra):
    _x = json.load(open(_extra))
    TERMS.update({k.lower(): tuple(v) for k, v in _x.get("terms", {}).items()})
    TERMS.update({k.lower(): tuple(v) for k, v in _x.get("sentences", {}).items()})
_keys = sorted(TERMS, key=len, reverse=True)
SEP = re.compile(r"(\s*(?:[;|:()]|(?<!\d),|,(?!\d))\s*|\s+-\s+|\s{2,}|\.\s*\*+\s*)")  # a comma between digits is a decimal comma, not a separator
PASS = re.compile(r"^[\d.,%×x\s/–-]*$|^<[^>]+>$|^[\d.,\s]+(?:%|g|kg|mg|µg|ug|mcg|iu|ie|iu/ui|ie/ui|kcal|kj|mg/kg|iu/kg|kcal/kg|kj/kg|mg/ kg|kcal/ kg|ml|l|°c)?\.?$", re.I)


def tr_term(t, lang):
    i = {"ru": 0, "hy": 1}[lang]
    k = t.strip().lower()
    if not k or PASS.match(k):
        return t, True
    tail = ""
    k = k.replace("\u2019", "\u2019")
    if k.endswith(".") and k[:-1] in TERMS:
        k, tail = k[:-1], "."
    k2 = re.sub(r"[*]+", "", k).strip()
    if k2 != k and k2 in TERMS:
        k = k2
    if k in TERMS:
        return TERMS[k][i] + tail, True
    # "chicken (58 %)"-style leftovers: split numeric tail ("Taurine 500 mg.", "total copper 5 mg/kg.")
    k = re.sub(r"\s*mg/\s*kg", " mg/kg", k)
    m = re.match(r"^(.*?)(\s*\d+[.,]?\d*\s*(?:%|g|kg|mg|µg|ug|mcg|iu|ie|iu/ui|ie/ui|mg/kg|iu/kg)?\.?)$", k)
    if m:
        head = re.sub(r"[*]+", "", m.group(1)).strip()      # "ginger* 0,005 %." -> "ginger"
        if head in TERMS:
            return TERMS[head][i] + m.group(2), True
    m = re.match(r"^(\d+[.,]?\d*\s*%?\s*)(.*)$", k)
    if m and m.group(2).strip() in TERMS:
        return m.group(1) + TERMS[m.group(2).strip()][i], True
    # multi-word phrase: translate word groups greedily
    words = k.split()
    out, ok, j = [], True, 0
    while j < len(words):
        hit = None
        for n in range(min(4, len(words) - j), 0, -1):
            ph = " ".join(words[j:j + n])
            if ph in TERMS:
                hit = (TERMS[ph][i], n); break
        if hit:
            out.append(hit[0]); j += hit[1]
        else:
            w = words[j]
            if PASS.match(w) or w in ("and", "with", "of", "from", "in"):
                out.append({"and": ("и", "և"), "with": ("с", "-ով"), "of": ("", ""), "from": ("из", "-ից"), "in": ("в", "-ում")}.get(w, (w, w))[i] if w in ("and", "with", "of", "from", "in") else w)
            else:
                out.append(w); ok = False
            j += 1
    return " ".join(x for x in out if x), ok


TAIL = ["gluten-free formula", "no added sugar", "with omega 3 and omega 6 fatty acids", "without cocoa", "vegetarian", "vegan",
        "store in a cool and dry place", "technological additives", "nutritional additives", "sensory additives", "zootechnical additives",
        "metabolisable energy", "metabolizable energy", "metabolized energy", "urine acidifying substance", "urine alkalising substance"]
TAILRE = re.compile(r"(?<![,:(])\s+(?=(" + "|".join(re.escape(t) for t in TAIL) + r")\b)", re.I)
VITRE = re.compile(r"\bvit\.\s*([a-z]\d*)\b", re.I)


def tr(line, lang, unknown=None):
    line = re.sub(r"<sub>(.*?)</sub>", r"\1", line)
    line = re.sub(r'<span[^>]*>(.*?)</span>', r"\1", line)
    line = VITRE.sub(lambda m: "vit-" + m.group(1).lower(), line)      # "Vit. E" -> one token
    line = TAILRE.sub(", ", line)
    line = re.sub(r"\.\s+(?=[A-Z])", ". | ", line)          # sentence boundary
    pre = ""
    m = re.match(r"^(<strong>)(.*?)(</strong>)\s*(.*)$", line, re.S)
    if m:
        lab, ok = tr_term(m.group(2).rstrip(":"), lang)
        pre = m.group(1) + lab + (":" if m.group(2).rstrip().endswith(":") else "") + m.group(3) + " "
        line = m.group(4)
    parts = SEP.split(line)
    out = [pre]
    for p in parts:
        if SEP.fullmatch(p) or not p.strip():
            out.append(p); continue
        t, ok = tr_term(p, lang)
        if not ok and unknown is not None:
            unknown.add(p.strip())
        out.append(t)
    return "".join(out).replace(". | ", ". ")


if __name__ == "__main__":
    if "--check" in sys.argv:
        src = json.load(open(sys.argv[sys.argv.index("--check") + 1]))
        lines = src if isinstance(src, list) else src.get("comps", [])
        unk = set()
        for l in lines:
            tr(l, "ru", unk)
        print(f"{len(lines)} lines, {len(unk)} unknown terms:")
        for u in sorted(unk):
            print("  ", u)
    else:
        print(tr(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "ru"))
