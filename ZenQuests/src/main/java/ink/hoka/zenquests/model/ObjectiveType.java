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
    // ── рыбалка ZenFishing ──
    CATCH_FISH,   // поймать рыбу ZenFishing               — цель: id рыбы из fish.yml (carp, sturgeon …) или ANY, +1
    CATCH_RARITY; // поймать рыбу редкости                 — цель: common/uncommon/rare/epic/legendary, +1

    public static ObjectiveType parse(String s) {
        if (s == null) return null;
        try { return valueOf(s.trim().toUpperCase()); } catch (IllegalArgumentException e) { return null; }
    }
}
