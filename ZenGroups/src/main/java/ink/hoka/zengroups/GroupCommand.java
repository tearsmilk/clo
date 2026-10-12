package ink.hoka.zengroups;

import ink.hoka.zengroups.util.Terms;
import ink.hoka.zengroups.util.Text;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * /group add <игрок> <группа> [срок]  — добавить (старые остаются; главная — с наибольшим весом)
 * /group set <игрок> <группа> [срок]  — установить (старые снимаются)
 * /group take <игрок> <группа>        — забрать
 * /group info <игрок> | list | reload
 */
public final class GroupCommand implements CommandExecutor, TabCompleter {

    private static final List<String> SUBS = List.of("add", "set", "take", "info", "list", "reload");
    private static final List<String> TERMS = List.of("1d", "7d", "30d", "90d", "forever");
    private final ZenGroups plugin;

    public GroupCommand(ZenGroups plugin) { this.plugin = plugin; }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!sender.hasPermission("zengroups.admin")) { plugin.msg(sender, "no-permission"); return true; }
        String sub = args.length == 0 ? "" : args[0].toLowerCase(Locale.ROOT);
        switch (sub) {
            case "reload" -> { plugin.reloadAll(); plugin.msg(sender, "reloaded", "groups", plugin.registry().size()); }
            case "list" -> {
                plugin.msg(sender, "list-header", "count", plugin.registry().size());
                List<Group> gs = new ArrayList<>(plugin.registry().all().values());
                gs.sort((a, b) -> Integer.compare(b.weight(), a.weight()));
                for (Group g : gs) plugin.msg(sender, "list-line", "group", g.id(), "weight", g.weight(), "prefix", g.chatPrefix());
            }
            case "info" -> {
                if (args.length < 2) { plugin.msg(sender, "usage"); return true; }
                OfflinePlayer t = offline(args[1]);
                if (t == null) { plugin.msg(sender, "player-unknown", "player", args[1]); return true; }
                plugin.msg(sender, "info-header", "player", name(t, args[1]), "primary", plugin.primary(t.getUniqueId()).id());
                List<UserStore.Entry> es = plugin.users().entries(t.getUniqueId(), null);
                if (es.isEmpty()) plugin.msg(sender, "info-empty", "default", plugin.defaultGroup());
                for (UserStore.Entry e : es) plugin.msg(sender, "info-line", "group", e.group, "time", left(e.until));
            }
            case "add", "set", "take" -> {
                if (args.length < 3) { plugin.msg(sender, "usage"); return true; }
                OfflinePlayer t = offline(args[1]);
                if (t == null) { plugin.msg(sender, "player-unknown", "player", args[1]); return true; }
                Group g = plugin.registry().get(args[2]);
                if (g == null) { plugin.msg(sender, "group-unknown", "group", args[2], "groups", String.join(", ", plugin.registry().all().keySet())); return true; }
                String pname = name(t, args[1]);
                if (sub.equals("take")) {
                    if (plugin.users().take(t.getUniqueId(), g.id())) {
                        plugin.msg(sender, "taken", "player", pname, "group", g.id());
                        if (t.getPlayer() != null) { plugin.msg(t.getPlayer(), "lost", "group", g.display()); plugin.refresh(t.getPlayer()); }
                    } else plugin.msg(sender, "not-in-group", "player", pname, "group", g.id());
                    return true;
                }
                Duration term;
                try { term = Terms.parse(args.length >= 4 ? args[3] : null); }
                catch (IllegalArgumentException ex) { plugin.msg(sender, "bad-term", "term", args[3]); return true; }
                Long ms = term == null ? null : term.toMillis();
                UserStore.Entry e = sub.equals("set") ? plugin.users().set(t.getUniqueId(), g.id(), ms) : plugin.users().add(t.getUniqueId(), g.id(), ms);
                plugin.msg(sender, sub.equals("set") ? "set" : "added", "player", pname, "group", g.id(), "time", left(e.until));
                if (t.getPlayer() != null) { plugin.msg(t.getPlayer(), "received", "group", g.display(), "time", left(e.until)); plugin.refresh(t.getPlayer()); }
            }
            default -> plugin.msg(sender, "usage");
        }
        return true;
    }

    private String name(OfflinePlayer t, String fallback) { return t.getName() != null ? t.getName() : fallback; }

    private OfflinePlayer offline(String name) {
        OfflinePlayer t = Bukkit.getPlayerExact(name);
        return t != null ? t : Bukkit.getOfflinePlayerIfCached(name);
    }

    public String left(long until) {
        if (until == UserStore.FOREVER) return plugin.getConfig().getString("messages.forever", "навсегда");
        return Text.duration(Duration.ofMillis(until - System.currentTimeMillis()));
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (!sender.hasPermission("zengroups.admin")) return List.of();
        if (args.length == 1) return filter(SUBS, args[0]);
        String sub = args[0].toLowerCase(Locale.ROOT);
        if (args.length == 2 && List.of("add", "set", "take", "info").contains(sub)) {
            List<String> n = new ArrayList<>(); for (Player p : Bukkit.getOnlinePlayers()) n.add(p.getName()); return filter(n, args[1]);
        }
        if (args.length == 3 && List.of("add", "set", "take").contains(sub)) return filter(new ArrayList<>(plugin.registry().all().keySet()), args[2]);
        if (args.length == 4 && List.of("add", "set").contains(sub)) return filter(TERMS, args[3]);
        return List.of();
    }

    private List<String> filter(List<String> opts, String pre) {
        List<String> out = new ArrayList<>();
        for (String o : opts) if (o.toLowerCase(Locale.ROOT).startsWith(pre.toLowerCase(Locale.ROOT))) out.add(o);
        return out;
    }
}
