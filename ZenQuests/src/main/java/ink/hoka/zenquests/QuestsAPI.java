package ink.hoka.zenquests;

import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import ink.hoka.zenquests.model.ObjectiveType;

/**
 * API для других плагинов (softdepend: [ZenQuests]):
 *   QuestsAPI.progress(player, "CROP_HARVEST", "wheat", 3);
 * Тип — как в quests.yml (BREAK, KILL, CROP_HARVEST …), цель — как в targets (может быть null).
 */
public final class QuestsAPI {
    private QuestsAPI() {}

    /** @return false, если плагин выключен или тип неизвестен. */
    public static boolean progress(Player player, String type, String target, int amount) {
        if (!(Bukkit.getPluginManager().getPlugin("ZenQuests") instanceof ZenQuests rq) || !rq.isEnabled()) return false;
        ObjectiveType t = ObjectiveType.parse(type);
        if (t == null || player == null || amount <= 0) return false;
        rq.quests().progress(player, t, target, amount);
        return true;
    }
}
