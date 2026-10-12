package ink.hoka.zenfishing.hook;

import ink.hoka.zenfishing.Fish;
import org.bukkit.entity.Player;

/**
 * ZenQuests: FISH по материалу предмета он считает сам из ванильного события. Мы засчитываем свои типы:
 * CATCH_FISH (цель — id рыбы) и CATCH_RARITY (цель — редкость). Второй рыбе из двойного улова ванильного
 * события нет — её засчитываем и как FISH по материалу.
 */
public final class QuestsHook {
    private QuestsHook() {}

    public static void progress(Player p, Fish f, boolean extra) {
        try {
            Class<?> api = Class.forName("ink.hoka.zenquests.QuestsAPI");
            var m = api.getMethod("progress", Player.class, String.class, String.class, int.class);
            m.invoke(null, p, "CATCH_FISH", f.id(), 1);
            m.invoke(null, p, "CATCH_RARITY", f.rarity().id(), 1);
            if (extra) m.invoke(null, p, "FISH", ink.hoka.zenfishing.FishItems.base(f.item()).getType().name(), 1);
        } catch (Throwable ignored) { }
    }
}
