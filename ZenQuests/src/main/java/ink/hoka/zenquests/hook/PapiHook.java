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
 *   %zenquests_hud_<n>_active% — 1, если есть n-й (1..4) невыполненный ежедневный квест, иначе 0 (для BetterHud)
 *   %zenquests_hud_<n>_name% / _desc / _progress / _amount / _percent / _left — название, первая строка описания, прогресс
 *   %zenquests_hud_count%      — сколько ежедневных ещё не выполнено
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
        if (params.toLowerCase().startsWith("hud_")) return hud(p, params.toLowerCase().substring(4));
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

    /** Невыполненные ежедневные квесты игрока по порядку — для плашек BetterHud. */
    private String hud(OfflinePlayer op, String key) {
        Player p = op.getPlayer();
        if (p == null) return key.endsWith("active") || key.equals("count") ? "0" : "";
        java.util.List<ink.hoka.zenquests.QuestManager.Entry> open = new java.util.ArrayList<>();
        for (ink.hoka.zenquests.QuestManager.Entry e : plugin.quests().entries(p, ink.hoka.zenquests.model.Category.DAILY))
            if (!plugin.quests().isDone(p, e)) open.add(e);
        if (key.equals("count")) return String.valueOf(open.size());
        int us = key.indexOf('_');
        if (us <= 0) return null;
        int n;
        try { n = Integer.parseInt(key.substring(0, us)); } catch (NumberFormatException ex) { return null; }
        String what = key.substring(us + 1);
        if (n < 1 || n > open.size()) return what.equals("active") ? "0" : "";
        ink.hoka.zenquests.QuestManager.Entry e = open.get(n - 1);
        int prog = Math.min(plugin.quests().data(p).get(e.key()), e.quest().amount()), amount = e.quest().amount();
        return switch (what) {
            case "active" -> "1";
            case "name" -> Text.strip(e.quest().name()).trim();
            case "desc" -> e.quest().description().isEmpty() ? "" : Text.strip(e.quest().description().get(0)).trim();
            case "progress" -> String.valueOf(prog);
            case "amount" -> String.valueOf(amount);
            case "left" -> String.valueOf(amount - prog);
            case "percent" -> String.valueOf(amount == 0 ? 100 : prog * 100 / amount);
            default -> null;
        };
    }

    /** В сети — полная проверка (право + выданная подписка), не в сети — только выданная командой. */
    private boolean isPremium(OfflinePlayer p) {
        Player online = p.getPlayer();
        if (online != null) return plugin.quests().isPremium(online);
        return plugin.premium().active(p.getUniqueId());
    }
}
