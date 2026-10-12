package ink.hoka.zenquests.hook;

import ink.hoka.zenquests.PremiumStore;
import ink.hoka.zenquests.ZenQuests;
import ink.hoka.zenquests.util.Text;
import me.clip.placeholderapi.expansion.PlaceholderExpansion;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.entity.Player;

import java.time.Duration;

/**
 * Плейсхолдеры PlaceholderAPI (нужен плагин PlaceholderAPI, иначе просто не регистрируемся):
 *   %zenquests_premium_badge%  — значок Ферма+ (premium.badge из config.yml) или пусто — для таба/чата
 *   %zenquests_premium%        — true / false
 *   %zenquests_premium_left%   — сколько осталось («3 д 4 ч», «навсегда») или пусто
 */
public final class PapiHook extends PlaceholderExpansion {

    private final ZenQuests plugin;

    private PapiHook(ZenQuests plugin) { this.plugin = plugin; }

    public static void tryRegister(ZenQuests plugin) {
        if (Bukkit.getPluginManager().getPlugin("PlaceholderAPI") == null) return;
        try {
            new PapiHook(plugin).register();
            plugin.getLogger().info("PlaceholderAPI найден — плейсхолдеры %zenquests_premium_badge%, %zenquests_premium%, %zenquests_premium_left%.");
        } catch (Throwable t) {
            plugin.getLogger().warning("PlaceholderAPI: не удалось зарегистрировать плейсхолдеры: " + t);
        }
    }

    @Override public String getIdentifier() { return "zenquests"; }
    @Override public String getAuthor() { return "nakuZen"; }
    @Override public String getVersion() { return plugin.getDescription().getVersion(); }
    @Override public boolean persist() { return true; }

    @Override
    public String onRequest(OfflinePlayer p, String params) {
        if (p == null) return "";
        boolean prem = isPremium(p);
        switch (params.toLowerCase()) {
            case "premium_badge": return plugin.getConfig().getString(prem ? "premium.badge" : "premium.badge-none", "");
            case "premium": return String.valueOf(prem);
            case "premium_left": {
                if (!prem) return "";
                Long until = plugin.premium().expires(p.getUniqueId());
                if (until == null) return plugin.getConfig().getString("messages.premium-forever", "навсегда");   // через право
                if (until == PremiumStore.FOREVER) return plugin.getConfig().getString("messages.premium-forever", "навсегда");
                return Text.duration(Duration.ofMillis(until - System.currentTimeMillis()));
            }
            default: return null;
        }
    }

    /** В сети — полная проверка (право + выданная подписка), не в сети — только выданная командой. */
    private boolean isPremium(OfflinePlayer p) {
        Player online = p.getPlayer();
        if (online != null) return plugin.quests().isPremium(online);
        return plugin.premium().active(p.getUniqueId());
    }
}
