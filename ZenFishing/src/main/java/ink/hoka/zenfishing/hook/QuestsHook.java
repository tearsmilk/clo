package ink.hoka.zenfishing.hook;

import ink.hoka.zenfishing.Fish;
import org.bukkit.entity.Player;

/**
 * ZenQuests: сам считает FISH по материалу предмета из ванильного события. Дополнительно засчитываем
 * цель «вид рыбы» (targets: [ZENFISH_<id>]) — чтобы делать квесты «поймай 3 осетра». Второй рыбе из двойного
 * улова ванильного события нет — её засчитываем и по материалу тоже.
 */
public final class QuestsHook {
    private QuestsHook() {}

    public static void progress(Player p, Fish f, boolean extra) {
        try {
            Class<?> api = Class.forName("ink.hoka.zenquests.QuestsAPI");
            var m = api.getMethod("progress", Player.class, String.class, String.class, int.class);
            m.invoke(null, p, "FISH", "ZENFISH_" + f.id().toUpperCase(java.util.Locale.ROOT), 1);
            if (extra) m.invoke(null, p, "FISH", ink.hoka.zenfishing.FishItems.base(f.item()).getType().name(), 1);
        } catch (Throwable ignored) { }
    }
}
