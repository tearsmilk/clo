package ink.hoka.zengroups;

import ink.hoka.zengroups.util.Text;
import net.kyori.adventure.text.Component;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.scoreboard.Scoreboard;
import org.bukkit.scoreboard.Team;

import java.util.Locale;

/** Таб (имя в списке) и над ником (команды главного скорборда: префикс, суффикс, сортировка по весу). */
public final class DisplayManager {

    private final ZenGroups plugin;

    public DisplayManager(ZenGroups plugin) { this.plugin = plugin; }

    public void apply(Player p) {
        Group g = plugin.primary(p.getUniqueId());
        if (plugin.getConfig().getBoolean("tab.enabled", true)) {
            String f = plugin.getConfig().getString("tab.format", "{prefix}{name}{suffix}");
            p.playerListName(Text.parse(f.replace("{prefix}", g.tabPrefix()).replace("{suffix}", g.tabSuffix()).replace("{name}", p.getName())));
        }
        if (plugin.getConfig().getBoolean("nametag.enabled", true) || plugin.getConfig().getBoolean("tab.sort", true)) {
            Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
            String name = teamName(g);
            Team t = sb.getTeam(name);
            if (t == null) t = sb.registerNewTeam(name);
            if (plugin.getConfig().getBoolean("nametag.enabled", true)) {
                t.prefix(Text.parse(g.namePrefix()));
                t.suffix(Text.parse(g.nameSuffix()));
            } else { t.prefix(Component.empty()); t.suffix(Component.empty()); }
            for (Team other : sb.getTeams()) if (other != t && other.getName().startsWith("zg") && other.hasEntry(p.getName())) other.removeEntry(p.getName());
            if (!t.hasEntry(p.getName())) t.addEntry(p.getName());
        }
    }

    /** Имя команды ≤16 символов; сортировка таба — по имени, поэтому вес «переворачивается»: чем больше вес, тем раньше. */
    private static String teamName(Group g) {
        String n = "zg" + String.format("%03d", Math.max(0, Math.min(999, 999 - g.weight()))) + "_" + g.id().toLowerCase(Locale.ROOT);
        return n.length() > 16 ? n.substring(0, 16) : n;
    }

    public void remove(Player p) {
        Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
        for (Team t : sb.getTeams()) if (t.getName().startsWith("zg") && t.hasEntry(p.getName())) t.removeEntry(p.getName());
    }

    public void applyAll() { for (Player p : Bukkit.getOnlinePlayers()) apply(p); }
}
