#!/usr/bin/env python3
"""Builds/merges reference/translations-attributes.json from the tables below.
Run each time a chunk is added; it reports every live value still untranslated."""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "reference/translations-attributes.json")
menu = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
data = json.load(open(OUT)) if os.path.exists(OUT) else {"_about": "en -> [ru, hy] for attribute names and value labels. Applied by scripts/translate-attributes.py once the backend stores per-locale labels.", "attributes": {}, "values": {}}

NAMES = {
 "product-weight": ("Вес упаковки", "Փաթեթի քաշ"), "food-form": ("Форма корма", "Կերի տեսակ"), "lifestage": ("Возраст", "Տարիք"),
 "breed-size": ("Размер породы", "Ցեղատեսակի չափ"), "flavor": ("Вкус", "Համ"), "special-diet": ("Особая диета", "Հատուկ դիետա"),
 "health-feature": ("Польза для здоровья", "Առողջական նշանակություն"), "texture": ("Текстура", "Հյուսվածք"), "packaging": ("Тип упаковки", "Փաթեթավորման տեսակ"),
 "toy-type": ("Тип игрушки", "Խաղալիքի տեսակ"), "material": ("Материал", "Նյութ"), "toy-feature": ("Особенность игрушки", "Խաղալիքի առանձնահատկություն"),
 "color-family": ("Цвет", "Գույն"), "toy-size": ("Размер игрушки", "Խաղալիքի չափ"), "ingredient": ("Ингредиент", "Բաղադրիչ"),
 "product-form": ("Форма выпуска", "Թողարկման ձև"), "active-ingredient": ("Действующее вещество", "Ակտիվ բաղադրիչ"),
}
V = {}
# --- generated: weights / volumes / sizes ---
def unit(label):
    m = re.match(r"^([\d.]+)\s*(kg|g|gr|l|cm)$", label)
    if not m: return None
    n, u = m.groups()
    ru = {"kg": "кг", "g": "г", "gr": "г", "l": "л", "cm": "см"}[u]
    hy = {"kg": "կգ", "g": "գ", "gr": "գ", "l": "լ", "cm": "սմ"}[u]
    return (f"{n} {ru}", f"{n} {hy}")
for code in ("product-weight", "toy-size"):
    for label in menu[code]["values"]:
        t = unit(label)
        if t: V.setdefault(code, {})[label] = t
# --- chunk 1 ---
V["lifestage"] = {"Adult": ("Взрослые", "Չափահաս"), "All Lifestages": ("Все возрасты", "Բոլոր տարիքների"), "Kitten": ("Котята", "Կատվի ձագեր"), "Nursing": ("Кормящие", "Կերակրող"), "Puppy": ("Щенки", "Քոթոթներ"), "Senior": ("Пожилые", "Տարեց")}
V["breed-size"] = {"All Breeds": ("Все породы", "Բոլոր ցեղատեսակները"), "Extra Small Breeds": ("Очень мелкие породы", "Շատ փոքր ցեղատեսակներ"), "Small Breeds": ("Мелкие породы", "Փոքր ցեղատեսակներ"), "Medium Breeds": ("Средние породы", "Միջին ցեղատեսակներ"), "Large Breeds": ("Крупные породы", "Խոշոր ցեղատեսակներ"), "Giant Breeds": ("Гигантские породы", "Հսկա ցեղատեսակներ")}
V["texture"] = {"Broth": ("В бульоне", "Արգանակով"), "Chunks in Gravy": ("Кусочки в соусе", "Կտորներ սոուսով"), "Chunks in Jelly": ("Кусочки в желе", "Կտորներ դոնդողով"), "Fillets": ("Филе", "Ֆիլե"), "Minced": ("Рубленый", "Մանրացված"), "Mousse": ("Мусс", "Մուս"), "Mousse & Shreds": ("Мусс с волокнами", "Մուս և թելիկներ"), "Pate": ("Паштет", "Պաշտետ"), "Shredded": ("Волокна", "Թելիկներ"), "Stew": ("Рагу", "Ռագու")}
V["packaging"] = {"Bag": ("Пакет", "Տոպրակ"), "Bottle": ("Бутылка", "Շիշ"), "Box": ("Коробка", "Տուփ"), "Can": ("Банка", "Պահածո"), "Cup": ("Стаканчик", "Բաժակ"), "Pouch": ("Пауч", "Պաուչ"), "Roll": ("Рулон", "Գլանափաթեթ"), "Shaker": ("Шейкер", "Շեյքեր"), "Tray": ("Ламистер", "Սկուտեղ"), "Tub": ("Контейнер", "Տարա"), "Tube": ("Тюбик", "Խողովակ"), "Variety Pack": ("Ассорти", "Հավաքածու")}
V["toy-type"] = {"Activity & Intelligence": ("Развивающие", "Զարգացնող"), "Ball": ("Мяч", "Գնդակ"), "Catnip": ("С кошачьей мятой", "Կատվախոտով"), "Chew & Dental": ("Жевательные и для зубов", "Ծամելու և ատամների"), "Fetch & Retrieve": ("Для апортировки", "Ապորտի"), "Latex & Rubber": ("Латекс и резина", "Լատեքս և ռետին"), "Mouse & Animal": ("Мышки и зверушки", "Մկնիկներ և կենդանիներ"), "Plush": ("Плюшевые", "Պլյուշե"), "Rope & Tug": ("Канаты и перетягивание", "Պարաններ և քաշքշուկ")}
V["food-form"] = {"Air-Dried": ("Сушёный на воздухе", "Օդում չորացրած"), "Dehydrated": ("Дегидрированный", "Ջրազրկված"), "Dried Fruits": ("Сушёные фрукты", "Չորացրած մրգեր"), "Dry Food": ("Сухой корм", "Չոր կեր"), "Food Topping": ("Топпинг", "Կերի հավելում"), "Freeze-Dried": ("Сублимированный", "Սառեցմամբ չորացրած"), "Frozen": ("Замороженный", "Սառեցված"), "Liquid": ("Жидкость", "Հեղուկ"), "Paste": ("Паста", "Մածուկ"), "Powder": ("Порошок", "Փոշի"), "Shelf Stable Fresh & Prepared Food": ("Готовый корм длительного хранения", "Երկար պահվող պատրաստի կեր"), "Sticks": ("Палочки", "Ձողիկներ"), "Tablets": ("Таблетки", "Հաբեր"), "Treats": ("Лакомства", "Հյուրասիրություններ"), "Wet Food": ("Влажный корм", "Թաց կեր")}
V["color-family"] = {"Multi": ("Разноцветный", "Բազմագույն"), "Brown": ("Коричневый", "Շագանակագույն"), "Blue": ("Синий", "Կապույտ"), "Green": ("Зелёный", "Կանաչ"), "Red": ("Красный", "Կարմիր"), "Yellow": ("Жёлтый", "Դեղին"), "Orange": ("Оранжевый", "Նարնջագույն"), "Pink": ("Розовый", "Վարդագույն"), "White": ("Белый", "Սպիտակ"), "Black": ("Чёрный", "Սև"), "Grey": ("Серый", "Մոխրագույն"), "Purple": ("Фиолетовый", "Մանուշակագույն"), "Color Varies": ("Цвет в ассортименте", "Գույնը տարբերվում է"), "Beige": ("Бежевый", "Բեժ"), "Glow In The Dark": ("Светится в темноте", "Լուսարձակող"), "Ivory": ("Слоновая кость", "Փղոսկրագույն"), "Gold": ("Золотой", "Ոսկեգույն"), "Clear": ("Прозрачный", "Թափանցիկ"), "Silver": ("Серебристый", "Արծաթագույն"), "Teal": ("Бирюзово-синий", "Կապտականաչ"), "Steel": ("Стальной", "Պողպատագույն"), "Turquoise": ("Бирюзовый", "Փիրուզագույն"), "Dark Blue": ("Тёмно-синий", "Մուգ կապույտ"), "Navy": ("Тёмно-синий (нэви)", "Ծովային կապույտ")}
V["toy-feature"] = {"Squeaky": ("С пищалкой", "Ճռճռանով"), "Tough Chewer": ("Для сильных жевателей", "Ուժեղ ծամողների համար"), "Exercise": ("Для активности", "Ակտիվության համար"), "Training": ("Для дрессировки", "Մարզման համար"), "Dental": ("Для зубов", "Ատամների համար"), "Teething": ("Для прорезывания зубов", "Ատամների ծլման համար"), "Outdoor": ("Для улицы", "Բացօթյա"), "Water Toy": ("Для воды", "Ջրային"), "Crinkle": ("Шуршащая", "Խշխշացող"), "Bouncy": ("Прыгучая", "Ցատկող"), "Stuffing-Free": ("Без наполнителя", "Առանց լցոնի"), "Variety Pack": ("Набор", "Հավաքածու"), "Durable": ("Прочная", "Ամուր"), "Electronic": ("Электронная", "Էլեկտրոնային"), "Glowing & Light-Up": ("Светящаяся", "Լուսարձակող"), "Puzzle Toy": ("Головоломка", "Գլուխկոտրուկ"), "Battery Operated": ("На батарейках", "Մարտկոցով"), "Replacement": ("Сменная часть", "Փոխարինող մաս"), "Herding": ("Пастушья", "Հովվական"), "Catnip": ("С кошачьей мятой", "Կատվախոտով"), "Floats": ("Плавающая", "Լողացող"), "Nylon": ("Нейлон", "Նեյլոն"), "TPR": ("TPR", "TPR"), "Natural": ("Натуральная", "Բնական"), "Spring": ("С пружиной", "Զսպանակով"), "Waterproof": ("Водонепроницаемая", "Ջրակայուն"), "Animal & Figure": ("Зверушки и фигурки", "Կենդանիներ և ֆիգուրներ"), "App-Controlled": ("Управление через приложение", "Հավելվածով կառավարվող"), "Scented": ("Ароматизированная", "Բուրավետ"), "Scratcher": ("Когтеточка", "Ճանկռոց"), "Massages Gums": ("Массирует дёсны", "Մերսում է լնդերը"), "Mint Flavour": ("Со вкусом мяты", "Անանուխի համով"), "Shock Absorber": ("С амортизатором", "Ամորտիզատորով"), "With Bell": ("С колокольчиком", "Զանգակով"), "With Rope": ("С верёвкой", "Պարանով")}
V["material"] = {"Chenille": ("Синель", "Շենիլ"), "Textilene": ("Текстилен", "Տեքստիլեն"), "Metal": ("Металл", "Մետաղ"), "Plastic": ("Пластик", "Պլաստիկ"), "Rubber": ("Резина", "Ռետին"), "Natural Fabric": ("Натуральная ткань", "Բնական գործվածք"), "Synthetic Fabric": ("Синтетическая ткань", "Սինթետիկ գործվածք"), "Wood": ("Дерево", "Փայտ"), "Rope": ("Канат", "Պարան"), "Cardboard / Paper": ("Картон / бумага", "Ստվարաթուղթ / թուղթ"), "Plant Material": ("Растительный материал", "Բուսական նյութ"), "Foam": ("Пена", "Փրփուր"), "Stainless Steel": ("Нержавеющая сталь", "Չժանգոտվող պողպատ"), "Leather": ("Кожа", "Կաշի"), "Nylon": ("Нейлон", "Նեյլոն"), "Silicone": ("Силикон", "Սիլիկոն"), "Polyester": ("Полиэстер", "Պոլիեսթեր"), "Cotton": ("Хлопок", "Բամբակ"), "Vinyl / PVC": ("Винил / ПВХ", "Վինիլ / PVC"), "Neoprene": ("Неопрен", "Նեոպրեն"), "Latex": ("Латекс", "Լատեքս"), "Aluminum": ("Алюминий", "Ալյումին"), "Bamboo": ("Бамбук", "Բամբուկ"), "Canvas": ("Канвас", "Կանվաս"), "Fleece": ("Флис", "Ֆլիս"), "Faux Leather": ("Искусственная кожа", "Արհեստական կաշի"), "Faux Fur": ("Искусственный мех", "Արհեստական մորթի"), "Hemp": ("Конопля", "Կանեփ"), "Corduroy": ("Вельвет", "Վելվետ"), "Wool": ("Шерсть", "Բուրդ"), "Felt": ("Фетр", "Թաղիք"), "Jute": ("Джут", "Ջուտ"), "Microfiber": ("Микрофибра", "Միկրոֆիբրա"), "Thermoplastic Rubber": ("Термопластичная резина", "Թերմոպլաստիկ ռետին"), "Acrylic": ("Акрил", "Ակրիլ"), "Coated Metal": ("Металл с покрытием", "Պատված մետաղ"), "Polypropylene": ("Полипропилен", "Պոլիպրոպիլեն"), "Polyurethane": ("Полиуретан", "Պոլիուրեթան"), "Nitrile": ("Нитрил", "Նիտրիլ"), "Ceramic": ("Керамика", "Կերամիկա"), "Glass": ("Стекло", "Ապակի"), "Stone": ("Камень", "Քար"), "Steel": ("Сталь", "Պողպատ"), "Mesh": ("Сетка", "Ցանց"), "Carpet": ("Ковровое покрытие", "Գորգ"), "Coated Steel": ("Сталь с покрытием", "Պատված պողպատ"), "Plush": ("Плюш", "Պլյուշ"), "Cotton/Polyester": ("Хлопок/полиэстер", "Բամբակ/պոլիեսթեր"), "Paper Cord": ("Бумажный шнур", "Թղթե պարան")}

for code, (ru, hy) in NAMES.items():
    data["attributes"][code] = [ru, hy]
for code, vals in V.items():
    for label, (ru, hy) in vals.items():
        data["values"].setdefault(code, {})[label] = [ru, hy]
json.dump(data, open(OUT, "w"), ensure_ascii=False, indent=1)
todo = {code: [l for l in m["values"] if l not in data["values"].get(code, {})] for code, m in menu.items()}
todo = {k: v for k, v in todo.items() if v}
print("attributes:", len(data["attributes"]), " values translated:", sum(len(v) for v in data["values"].values()))
print("still untranslated:", {k: len(v) for k, v in todo.items()})
for k, v in todo.items():
    print(f"  {k}: {' · '.join(v)}")
