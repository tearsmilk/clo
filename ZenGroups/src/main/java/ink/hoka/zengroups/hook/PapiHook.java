package ink.hoka.zengroups.hook;

import ink.hoka.zengroups.Group;
import ink.hoka.zengroups.UserStore;
import ink.hoka.zengroups.ZenGroups;
import ink.hoka.zengroups.util.Text;
import me.clip.placeholderapi.expansion.PlaceholderExpansion;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;

import java.time.Duration;
import java.util.List;

/**
 * %zengroups_group% / %zengroups_group_display% / %zengroups_weight%
 * %zengroups_tab_prefix% %zengroups_tab_suffix% %zengroups_chat_prefix% %zengroups_chat_suffix% %zengroups_name_prefix% %zengroups_name_suffix%
 * %zengroups_time% — сколько осталось у главной группы; %zengroups_has_<группа>% — true/false
 */
public final class PapiHook extends PlaceholderExpansion {

    private final ZenGroups plugin;

    private PapiHook(ZenGroups plugin) { this.plugin = plugin; }

    public static void tryRegister(ZenGroups plugin) {
        if (Bukkit.getPluginManager().getPlugin("PlaceholderAPI") == null) return;
        try { new PapiHook(plugin).register(); plugin.getLogger().info("PlaceholderAPI найден — плейсхолдеры %zengroups_*%."); }
        catch (Throwable t) { plugin.getLogger().warning("PlaceholderAPI: " + t); }
    }

    @Override public String getIdentifier() { return "zengroups"; }
    @Override public String getAuthor() { return "nakuZen"; }
    @Override public String getVersion() { return plugin.getDescription().getVersion(); }
    @Override public boolean persist() { return true; }

    @Override
    public String onRequest(OfflinePlayer p, String params) {
        if (p == null) return "";
        Group g = plugin.primary(p.getUniqueId());
        String k = params.toLowerCase();
        if (k.startsWith("has_")) {
            String id = k.substring(4);
            for (Group x : plugin.groupsOf(p.getUniqueId())) if (x.id().equals(id)) return "true";
            return "false";
        }
        return switch (k) {
            case "group" -> g.id();
            case "group_display" -> g.display();
            case "weight" -> String.valueOf(g.weight());
            case "tab_prefix" -> g.tabPrefix();
            case "tab_suffix" -> g.tabSuffix();
            case "chat_prefix" -> g.chatPrefix();
            case "chat_suffix" -> g.chatSuffix();
            case "name_prefix" -> g.namePrefix();
            case "name_suffix" -> g.nameSuffix();
            case "time" -> {
                UserStore.Entry e = plugin.users().entry(p.getUniqueId(), g.id());
                if (e == null || e.until == UserStore.FOREVER) yield plugin.getConfig().getString("messages.forever", "навсегда");
                yield Text.duration(Duration.ofMillis(e.until - System.currentTimeMillis()));
            }
            default -> null;
        };
    }
}
