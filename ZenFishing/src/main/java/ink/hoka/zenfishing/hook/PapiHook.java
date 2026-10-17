package ink.hoka.zenfishing.hook;

import ink.hoka.zenfishing.PlayerStats;
import ink.hoka.zenfishing.ZenFishing;
import ink.hoka.zenfishing.util.Text;
import me.clip.placeholderapi.expansion.PlaceholderExpansion;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;


/**
 * %zenfishing_premium% — есть ли Ферма+ (сама подписка — в ZenQuests: %zenquests_premium_badge% и т.п.)
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
        switch (params.toLowerCase()) {
            case "premium": return String.valueOf(on != null && plugin.isPremium(on));
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
