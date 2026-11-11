PRESETS = (
    {
        "id": "visual",
        "title": "Визуал",
        "summary": "Шейдеры, анимации рук в духе Punchy, плащи, листва, частицы, шаги и небо. Мир выглядит живым.",
        "mods": {
            "fabric": (
                "fabric-api", "sodium", "iris", "sodium-extra", "lambdynamiclights", "continuity",
                "punchy", "not-enough-animations", "entity-model-features", "fallingleaves",
                "visuality", "wavey-capes", "presence-footsteps",
            ),
            "quilt": (
                "sodium", "iris", "continuity", "punchy", "not-enough-animations",
                "fallingleaves", "visuality", "wavey-capes",
            ),
            "forge": (
                "embeddium", "oculus", "continuity", "punchy", "entity-model-features",
                "visuality", "effective", "lambdynamiclights", "presence-footsteps",
            ),
            "neoforge": (
                "embeddium", "oculus", "continuity", "punchy", "entity-model-features",
                "visuality", "effective", "lambdynamiclights", "presence-footsteps",
            ),
        },
        "shaders": ("complementary-reimagined",),
    },
    {
        "id": "zombie",
        "title": "Зомби-выживание",
        "summary": "Орды, умные зомби, жажда и могилы. Обычное выживание становится опасным.",
        "mods": {
            "fabric": ("fabric-api", "rottencreatures", "zombie-awareness", "tough-as-nails", "universal-graves"),
            "quilt": ("rottencreatures", "tough-as-nails", "universal-graves"),
            "forge": ("rottencreatures", "zombie-awareness", "tough-as-nails", "gravestone-mod", "enhanced-ai"),
            "neoforge": ("rottencreatures", "zombie-awareness", "tough-as-nails", "gravestone-mod", "enhanced-ai"),
        },
    },
    {
        "id": "survival",
        "title": "Выживание",
        "summary": "Еда, сезоны, жажда, рюкзак пути, карта и могила, если умрёшь.",
        "mods": {
            "fabric": (
                "fabric-api", "farmers-delight", "supplementaries", "tough-as-nails", "serene-seasons",
                "comforts", "waystones", "appleskin", "jade", "xaeros-minimap", "universal-graves",
            ),
            "quilt": ("farmers-delight", "supplementaries", "tough-as-nails", "serene-seasons", "waystones", "xaeros-minimap"),
            "forge": (
                "cloth-config", "farmers-delight", "supplementaries", "tough-as-nails", "serene-seasons",
                "comforts", "waystones", "appleskin", "jade", "xaeros-minimap", "gravestone-mod",
            ),
            "neoforge": (
                "cloth-config", "farmers-delight", "supplementaries", "tough-as-nails", "serene-seasons",
                "waystones", "appleskin", "jade", "xaeros-minimap", "gravestone-mod",
            ),
        },
    },
    {
        "id": "weapons",
        "title": "Оружие",
        "summary": "Мечи, древковое оружие, перекаты и мушкеты. Бой перестаёт быть ванильным.",
        "mods": {
            "fabric": ("fabric-api", "better-combat", "simply-swords", "spartan-weaponry", "combat-roll", "musket-mod"),
            "quilt": ("better-combat", "simply-swords", "spartan-weaponry", "combat-roll"),
            "forge": ("better-combat", "simply-swords", "spartan-weaponry", "combat-roll", "musket-mod"),
            "neoforge": ("better-combat", "simply-swords", "spartan-weaponry", "combat-roll"),
        },
    },
    {
        "id": "machines",
        "title": "Механизмы и физика",
        "summary": "Create, рельсы, паровозы и физика Valyrien Skies: корабли, дирижабли и механизмы, которые правда двигаются.",
        "mods": {
            "fabric": (
                "fabric-api", "create", "valkyrien-skies", "clockwork", "eureka",
                "trackwork", "create-steam-n-rails", "createaddition",
            ),
            "quilt": ("create", "valkyrien-skies", "clockwork", "eureka"),
            "forge": (
                "create", "valkyrien-skies", "clockwork", "eureka",
                "trackwork", "create-steam-n-rails", "createaddition",
            ),
            "neoforge": (
                "create", "valkyrien-skies", "clockwork", "eureka",
                "trackwork", "create-steam-n-rails", "createaddition",
            ),
        },
    },
    {
        "id": "magic",
        "title": "Магия",
        "summary": "Ботания, заклинания и конфиги, чтобы магия не ломала меню.",
        "mods": {
            "fabric": ("fabric-api", "cloth-config", "botania"),
            "quilt": ("cloth-config", "botania"),
            "forge": ("cloth-config", "botania", "ars-nouveau"),
            "neoforge": ("cloth-config", "botania", "ars-nouveau"),
        },
    },
    {
        "id": "optimize",
        "title": "Оптимизация",
        "summary": "Только то, что поднимает кадры: рендер, тики и память. Шейдеров нет.",
        "mods": {
            "fabric": ("fabric-api", "sodium", "lithium", "ferrite-core", "entityculling", "immediatelyfast"),
            "quilt": ("sodium", "lithium", "ferrite-core", "immediatelyfast"),
            "forge": ("embeddium", "modernfix", "ferrite-core", "entityculling"),
            "neoforge": ("embeddium", "modernfix", "ferrite-core", "entityculling"),
        },
    },
    {
        "id": "vanilla_plus",
        "title": "Ванильное+",
        "summary": "Почти ваниль: оптимизация, подсказка еды и миникарта. Без больших модов.",
        "mods": {
            "fabric": ("fabric-api", "sodium", "lithium", "ferrite-core", "appleskin", "xaeros-minimap"),
            "quilt": ("sodium", "lithium", "ferrite-core", "appleskin", "xaeros-minimap"),
            "forge": ("embeddium", "ferrite-core", "appleskin", "xaeros-minimap"),
            "neoforge": ("embeddium", "ferrite-core", "appleskin", "xaeros-minimap"),
        },
    },
)

CURATED = (
    {
        "words": ("шейд", "shader", "iris", "окулус"),
        "title": "Шейдеры",
        "summary": "Картинка с шейдерами без OptiFine: Iris или Oculus плюс быстрый рендер. Пак шейдеров кладётся в shaderpacks.",
        "mods": {
            "fabric": ("sodium", "iris", "fabric-api"),
            "quilt": ("sodium", "iris"),
            "forge": ("embeddium", "oculus"),
            "neoforge": ("embeddium", "oculus"),
        },
        "shaders": ("complementary-reimagined",),
    },
    {
        "words": ("анимац", "animat", "эмф"),
        "title": "Анимации",
        "summary": "Анимации рук, предметов и модели: Not Enough Animations, EMF и ETF.",
        "mods": {
            "fabric": ("fabric-api", "not-enough-animations", "entity-model-features", "entity-texture-features"),
            "quilt": ("not-enough-animations", "entity-model-features", "entity-texture-features"),
            "forge": ("not-enough-animations", "entity-model-features", "entity-texture-features"),
            "neoforge": ("not-enough-animations", "entity-model-features", "entity-texture-features"),
        },
    },
    {
        "words": ("зомби", "zombie", "апокал", "нежить", "орда"),
        "title": "Зомби-выживание",
        "summary": "Орды и умные зомби, тяжёлое выживание и могилы. Уже стоящие моды повторно не качаются.",
        "mods": {
            "fabric": ("fabric-api", "rottencreatures", "zombie-awareness", "tough-as-nails", "universal-graves"),
            "quilt": ("rottencreatures", "tough-as-nails", "universal-graves"),
            "forge": ("rottencreatures", "zombie-awareness", "tough-as-nails", "gravestone-mod", "enhanced-ai"),
            "neoforge": ("rottencreatures", "zombie-awareness", "tough-as-nails", "gravestone-mod", "enhanced-ai"),
        },
    },
    {
        "words": ("ужас", "хоррор", "horror", "туман"),
        "title": "Хоррор",
        "summary": "Жуткий набор: туман и ощущение, что за тобой следят.",
        "mods": {
            "fabric": ("fabric-api", "from-the-fog"),
            "quilt": ("from-the-fog",),
            "forge": ("from-the-fog",),
            "neoforge": ("from-the-fog",),
        },
    },
    {
        "words": ("оптим", "фпс", "fps", "лаг", "натрий", "sodium", "произв"),
        "title": "Оптимизация",
        "summary": "Сборка для кадров: легче рендер, тики и лишние сущности. Шейдеров нет.",
        "mods": {
            "fabric": ("sodium", "lithium", "ferrite-core", "entityculling", "immediatelyfast", "fabric-api"),
            "quilt": ("sodium", "lithium", "ferrite-core", "immediatelyfast"),
            "forge": ("embeddium", "modernfix", "ferrite-core", "entityculling"),
            "neoforge": ("embeddium", "modernfix", "ferrite-core", "entityculling"),
        },
    },
    {
        "words": ("маг", "magic", "волшеб", "закл", "ботан"),
        "title": "Магия",
        "summary": "Магический набор: ботания, заклинания и библиотека конфигов.",
        "mods": {
            "fabric": ("fabric-api", "cloth-config", "botania"),
            "quilt": ("cloth-config", "botania"),
            "forge": ("cloth-config", "botania", "ars-nouveau"),
            "neoforge": ("cloth-config", "botania", "ars-nouveau"),
        },
    },
    {
        "words": ("тех", "tech", "механ", "create", "криэйт", "завод"),
        "title": "Техника",
        "summary": "Небольшая техническая сборка вокруг Create и удобных подсказок.",
        "mods": {
            "fabric": ("fabric-api", "cloth-config", "create"),
            "quilt": ("cloth-config", "create"),
            "forge": ("cloth-config", "create"),
            "neoforge": ("cloth-config", "create"),
        },
    },
    {
        "words": ("данж", "приключ", "advent", "yung", "пещер"),
        "title": "Данжи",
        "summary": "Больше структур и данжей, плюс карта и подсказки по мобам.",
        "mods": {
            "fabric": ("fabric-api", "cloth-config", "yungs-better-dungeons", "jade", "xaeros-minimap"),
            "quilt": ("yungs-better-dungeons", "jade", "xaeros-minimap"),
            "forge": ("yungs-better-dungeons", "jade", "xaeros-minimap"),
            "neoforge": ("yungs-better-dungeons", "jade", "xaeros-minimap"),
        },
    },
    {
        "words": ("уют", "декор", "еда", "farm", "дерев"),
        "title": "Уют",
        "summary": "Декор и еда: Farmer's Delight и Supplementaries.",
        "mods": {
            "fabric": ("fabric-api", "cloth-config", "farmers-delight", "supplementaries"),
            "quilt": ("farmers-delight", "supplementaries"),
            "forge": ("cloth-config", "farmers-delight", "supplementaries"),
            "neoforge": ("cloth-config", "farmers-delight", "supplementaries"),
        },
    },
    {
        "words": ("pvp", "пвп", "мини", "xaero"),
        "title": "PvP",
        "summary": "Лёгкий PvP-набор: карта, яблоки на голоде и оптимизация кадра.",
        "mods": {
            "fabric": ("fabric-api", "sodium", "appleskin", "xaeros-minimap", "xaeros-world-map"),
            "quilt": ("sodium", "appleskin", "xaeros-minimap"),
            "forge": ("embeddium", "appleskin", "xaeros-minimap", "xaeros-world-map"),
            "neoforge": ("embeddium", "appleskin", "xaeros-minimap", "xaeros-world-map"),
        },
    },
)

