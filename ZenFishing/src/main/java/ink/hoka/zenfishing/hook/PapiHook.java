package ink.hoka.zenfishing.hook;

import ink.hoka.zenfishing.PlayerStats;
import ink.hoka.zenfishing.PremiumStore;
import ink.hoka.zenfishing.ZenFishing;
import ink.hoka.zenfishing.util.Text;
import me.clip.placeholderapi.expansion.PlaceholderExpansion;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;

import java.time.Duration;

/**
 * %zenfishing_premium_badge% / %zenfishing_premium% / %zenfishing_premium_left% — подписка Рыбак+
 * %zenfishing_level% / %zenfishing_xp% / %zenfishing_need% — удочка в руке (пусто, если её нет)
 * %zenfishing_caught% / %zenfishing_known% / %zenfishing_earned% — статистика
 */
public final class PapiHook extends PlaceholderExpansion {

    private final ZenFishing plugin;

    private PapiHook(ZenFishing plugin) { this.plugin = plugin; }

    public static void tryRegister(ZenFishing plugin) {
        if (Bukkit.getPluginManager().getPlugin("PlaceholderAPI") == null) return;
        try { new PapiHook(plugin).register(); plugin.getLogger().info("PlaceholderAPI найден — плейсхолдеры %zenfishing_*%."); }
        catch (Throwable t) { plugin.getLogger().warning("PlaceholderAPI: " + t); }
    }

    @Override public String getIdentifier() { return "zenfishing"; }
    @Override public String getAuthor() { return "nakuZen"; }
    @Override public String getVersion() { return plugin.getDescription().getVersion(); }
    @Override public boolean persist() { return true; }

    @Override
    public String onRequest(OfflinePlayer p, String params) {
        if (p == null) return "";
        Player on = p.getPlayer();
        boolean prem = on != null ? plugin.isPremium(on) : plugin.premium().active(p.getUniqueId());
        switch (params.toLowerCase()) {
            case "premium_badge": return plugin.getConfig().getString(prem ? "premium.badge" : "premium.badge-none", "");
            case "premium": return String.valueOf(prem);
            case "premium_left": {
                if (!prem) return "";
                Long until = plugin.premium().expires(p.getUniqueId());
                if (until == null || until == PremiumStore.FOREVER) return plugin.getConfig().getString("messages.premium-forever", "навсегда");
                return Text.duration(Duration.ofMillis(until - System.currentTimeMillis()));
            }
            case "level": case "xp": case "need": {
                if (on == null) return "";
                ItemStack rod = on.getInventory().getItemInMainHand();
                if (!plugin.rods().isRod(rod)) rod = on.getInventory().getItemInOffHand();
                if (!plugin.rods().isRod(rod)) return "";
                int lvl = plugin.rods().level(rod);
                return params.equalsIgnoreCase("level") ? String.valueOf(lvl) : params.equalsIgnoreCase("xp") ? String.valueOf(plugin.rods().xp(rod)) : String.valueOf(plugin.rods().need(lvl));
            }
            case "caught": case "known": case "earned": {
                PlayerStats s = on != null ? plugin.stats().get(on) : plugin.stats().peek(p);
                return params.equalsIgnoreCase("caught") ? String.valueOf(s.caught) : params.equalsIgnoreCase("known") ? String.valueOf(s.known()) : Text.num(s.earned);
            }
            default: return null;
        }
    }
}
