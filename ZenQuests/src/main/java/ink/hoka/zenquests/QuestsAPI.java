package ink.hoka.zenquests;

import org.bukkit.entity.Player;
import ink.hoka.zenquests.model.ObjectiveType;

/**
 * API для других плагинов (dependency: Noratrum):
 *   QuestsAPI.progress(player, "CROP_HARVEST", "wheat", 3);
 * Тип — как в quests.yml (BREAK, KILL, CROP_HARVEST …), цель — как в targets (может быть null).
 */
public final class QuestsAPI {
    private QuestsAPI() {}

    private static ZenQuests module() {
        ink.hoka.noratrum.Noratrum n = ink.hoka.noratrum.Noratrum.get();
        return n == null || !n.isEnabled() ? null : n.quests();
    }

    /** Есть ли у игрока подписка Ферма+ (право или выдача командой). Ею же пользуется ZenFishing. */
    public static boolean isPremium(Player player) {
        ZenQuests rq = module();
        if (rq == null || player == null) return false;
        return rq.quests().isPremium(player);
    }

    /** @return false, если плагин выключен или тип неизвестен. */
    public static boolean progress(Player player, String type, String target, int amount) {
        ZenQuests rq = module();
        if (rq == null) return false;
        ObjectiveType t = ObjectiveType.parse(type);
        if (t == null || player == null || amount <= 0) return false;
        rq.quests().progress(player, t, target, amount);
        return true;
    }
}
