package ink.hoka.zenboosters;

import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * /бустер                                   — свои активные бустеры
 * /бустер give <игрок> <тип> <x> <время>    — личный бустер (admin)
 * /бустер global <тип> <x> <время>          — глобальный (admin)
 * /бустер list [игрок]  |  clear <игрок|global> [тип]  |  reload   (admin)
 * Время: 30m, 2h, 1d, 1h30m (голое число — минуты).
 */
public final class BoosterCommand implements CommandExecutor, TabCompleter {

    private final ZenBoosters plugin;
    public BoosterCommand(ZenBoosters plugin) { this.plugin = plugin; }
    private BoosterManager m() { return plugin.manager(); }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        String sub = args.length == 0 ? "" : args[0].toLowerCase(Locale.ROOT);
        if (sub.isEmpty()) {
            if (!(sender instanceof Player p)) { plugin.msg(sender, "usage-admin"); return true; }
            show(sender, p.getUniqueId(), p.getName());
            return true;
        }
        if (!sender.hasPermission("zenboosters.admin")) { plugin.msg(sender, "no-permission"); return true; }
        switch (sub) {
            case "give", "дать" -> {
                if (args.length < 5) { plugin.msg(sender, "usage-admin"); return true; }
                OfflinePlayer t = offline(args[1]);
                if (t == null) { plugin.msg(sender, "player-unknown", "player", args[1]); return true; }
                BoosterManager.Type type = m().type(args[2]);
                if (type == null) { plugin.msg(sender, "unknown-type", "type", args[2], "types", String.join(", ", m().types().keySet())); return true; }
                double mult = parseMult(args[3]); long ms = BoosterManager.parseTime(args[4]);
                if (mult <= 1 || ms <= 0) { plugin.msg(sender, "usage-admin"); return true; }
                m().addPersonal(t.getUniqueId(), type.id(), mult, ms, sender.getName());
                plugin.msg(sender, "given", "player", t.getName() != null ? t.getName() : args[1], "type", type.name(), "mult", BoosterManager.fmt(mult), "left", BoosterManager.time(ms));
                Player on = t.getPlayer();
                if (on != null) plugin.msg(on, "received", "type", type.name(), "mult", BoosterManager.fmt(mult), "left", BoosterManager.time(ms));
            }
            case "global", "глобал", "всем" -> {
                if (args.length < 4) { plugin.msg(sender, "usage-admin"); return true; }
                BoosterManager.Type type = m().type(args[1]);
                if (type == null) { plugin.msg(sender, "unknown-type", "type", args[1], "types", String.join(", ", m().types().keySet())); return true; }
                double mult = parseMult(args[2]); long ms = BoosterManager.parseTime(args[3]);
                if (mult <= 1 || ms <= 0) { plugin.msg(sender, "usage-admin"); return true; }
                m().addGlobal(type.id(), mult, ms, sender.getName());
                plugin.broadcast("global-started", "type", type.name(), "mult", BoosterManager.fmt(mult), "left", BoosterManager.time(ms), "by", sender.getName());
            }
            case "list", "список" -> {
                if (args.length >= 2) { OfflinePlayer t = offline(args[1]); if (t == null) { plugin.msg(sender, "player-unknown", "player", args[1]); return true; } show(sender, t.getUniqueId(), t.getName() != null ? t.getName() : args[1]); }
                else show(sender, null, null);
            }
            case "clear", "снять" -> {
                if (args.length < 2) { plugin.msg(sender, "usage-admin"); return true; }
                String type = args.length >= 3 ? args[2] : null;
                if (args[1].equalsIgnoreCase("global")) { plugin.msg(sender, "cleared", "count", m().clear(null, type), "player", "global"); return true; }
                OfflinePlayer t = offline(args[1]);
                if (t == null) { plugin.msg(sender, "player-unknown", "player", args[1]); return true; }
                plugin.msg(sender, "cleared", "count", m().clear(t.getUniqueId(), type), "player", t.getName() != null ? t.getName() : args[1]);
            }
            case "reload" -> { plugin.reloadAll(); plugin.msg(sender, "reloaded", "count", m().types().size()); }
            default -> plugin.msg(sender, "usage-admin");
        }
        return true;
    }

    private void show(CommandSender to, java.util.UUID id, String name) {
        List<BoosterManager.Booster> g = m().global();
        plugin.msg(to, "list-header-global", "count", g.size());
        for (BoosterManager.Booster b : g) plugin.msg(to, "list-line", "type", m().name(b.type), "mult", BoosterManager.fmt(b.mult), "left", BoosterManager.time(b.left()), "by", b.by);
        if (id != null) {
            List<BoosterManager.Booster> p = m().personal(id);
            plugin.msg(to, "list-header-personal", "player", name, "count", p.size());
            for (BoosterManager.Booster b : p) plugin.msg(to, "list-line", "type", m().name(b.type), "mult", BoosterManager.fmt(b.mult), "left", BoosterManager.time(b.left()), "by", b.by);
            if (g.isEmpty() && p.isEmpty()) plugin.msg(to, "list-empty");
        }
    }

    private static double parseMult(String s) {
        try { return Double.parseDouble(s.toLowerCase(Locale.ROOT).replace("x", "").replace("х", "").replace(',', '.')); } catch (NumberFormatException e) { return 0; }
    }

    private static OfflinePlayer offline(String name) {
        Player on = Bukkit.getPlayerExact(name);
        if (on != null) return on;
        OfflinePlayer op = Bukkit.getOfflinePlayerIfCached(name);
        return op != null && (op.hasPlayedBefore() || op.isOnline()) ? op : null;
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (!sender.hasPermission("zenboosters.admin")) return List.of();
        List<String> names = new ArrayList<>(); for (Player p : Bukkit.getOnlinePlayers()) names.add(p.getName());
        List<String> types = new ArrayList<>(m().types().keySet());
        if (args.length == 1) return filter(List.of("give", "global", "list", "clear", "reload"), args[0]);
        String s = args[0].toLowerCase(Locale.ROOT);
        if (s.equals("give")) return switch (args.length) { case 2 -> filter(names, args[1]); case 3 -> filter(types, args[2]); case 4 -> filter(List.of("1.5", "2", "3"), args[3]); case 5 -> filter(List.of("30m", "1h", "3h", "1d"), args[4]); default -> List.of(); };
        if (s.equals("global")) return switch (args.length) { case 2 -> filter(types, args[1]); case 3 -> filter(List.of("1.5", "2", "3"), args[2]); case 4 -> filter(List.of("30m", "1h", "3h", "1d"), args[3]); default -> List.of(); };
        if (s.equals("list") && args.length == 2) return filter(names, args[1]);
        if (s.equals("clear")) { if (args.length == 2) { List<String> l = new ArrayList<>(List.of("global")); l.addAll(names); return filter(l, args[1]); } if (args.length == 3) return filter(types, args[2]); }
        return List.of();
    }

    private static List<String> filter(List<String> in, String pref) {
        String p = pref.toLowerCase(Locale.ROOT); List<String> out = new ArrayList<>();
        for (String s : in) if (s.toLowerCase(Locale.ROOT).startsWith(p)) out.add(s);
        return out;
    }
}
