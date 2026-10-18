package ink.hoka.zenquests.model;

/**
 * Что нужно сделать. Цель (targets) — имена из Minecraft:
 * блоки/предметы (STONE, OAK_LOG, COD …) или сущности (ZOMBIE, COW, PLAYER …).
 */
public enum ObjectiveType {
    BREAK,      // сломать блок            — цель: блок
    PLACE,      // поставить блок          — цель: блок
    KILL,       // убить моба/игрока       — цель: сущность
    FISH,       // выловить                — цель: предмет
    CRAFT,      // скрафтить               — цель: предмет
    SMELT,      // забрать из печи         — цель: предмет
    EAT,        // съесть/выпить           — цель: предмет
    ENCHANT,    // зачаровать              — цель: предмет
    BREED,      // развести                — цель: сущность
    TAME,       // приручить               — цель: сущность
    WALK,       // пройти блоков           — без цели
    PLAYTIME,   // наиграть минут          — без цели
    // ── фермы TakuFarmers (кастомные культуры, удары мотыгой) ── цель: id культуры (wheat …)
    CROP_HIT,     // удачный удар по выросшему растению (HARVEST или BREAK), +1
    CROP_HARVEST, // собрано урожая, + сколько выпало
    CROP_BREAK,   // растение срублено полностью (последний удар цикла), +1
    COOK,         // готовка на станции завершена          — цель: id станции, +1
    COOK_ITEM,    // приготовлено блюдо                    — цель: предмет-результат, + сколько
    MILL,         // перемолото на жёрнове                 — цель: предмет-результат, + сколько выдано
    FLOUR_SACK,   // скрафчен мешок муки                   — без цели, +1
    EARN,         // заработано валюты                     — цель: COINS или GEMS, + сумма
    SPEND,        // потрачено валюты                      — цель: COINS или GEMS, + сумма
    FARM_VISIT,   // зайти на свою ферму                   — без цели, +1
    NPC_TALK,     // клик по NPC                           — цель: id NPC, +1
    DIALOG,       // диалог с NPC (F)                      — цель: id диалога, +1
    SEEDS,        // переработать растения в семена на столе семян — цель: id семян (seed_wheat …) или ANY, + сколько забрано
    // ── грядки TakuFarmers (BedActionEvent, API 1.1+) ── цель: id культуры грядки (farm_wheat, farm_tomato …) или ANY
    WEED,         // прополоть грядку мотыгой              +1
    WATER,        // полить грядку лейкой                  +1
    WELL,         // полить все грядки волшебным колодцем  без цели, +1 за использование
    FERTILIZE,    // удобрить грядку                       +1
    BED_PLACE,    // поставить грядку                      без цели, +1
    BED_PLANT,    // посадить на грядку                    +1
    BED_HARVEST,  // дорастить и срезать культуру на грядке +1
    // ── рыбалка ZenFishing ──
    CATCH_FISH,   // поймать рыбу ZenFishing               — цель: id рыбы из fish.yml (carp, sturgeon …) или ANY, +1
    CATCH_RARITY, // поймать рыбу редкости                 — цель: common/uncommon/rare/epic/legendary, +1
    CATCH_NIGHT,  // поймать рыбу ночью                    — цель: id рыбы или ANY, +1
    CATCH_BIG,    // поймать трофейную рыбу (≥ big-kg)     — цель: id рыбы или ANY, +1
    FISH_EARN,    // заработано продажей рыбы (/рыбалка продать, меню) — цель: COINS, + сумма
    // ── предметы ──
    OBTAIN;       // получить предмет в инвентарь (жёрнов, покупка, подбор…) — цель: материал или id Nexo (flour), + прирост

    public static ObjectiveType parse(String s) {
        if (s == null) return null;
        try { return valueOf(s.trim().toUpperCase()); } catch (IllegalArgumentException e) { return null; }
    }
}
