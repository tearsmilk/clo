package ink.hoka.zenfishing;

import ink.hoka.zenfishing.util.Text;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * /рыбалка                — меню
 * /рыбалка продать        — продать всю рыбу
 * /рыбалка топ            — топ рыбаков
 * /рыбалка журнал [игрок] — выдать рыбацкий журнал (другому — zenfishing.admin)
 * /рыбалка сеть [игрок]   — выдать рыболовную сеть себе/игроку; list | clear [игрок] — только zenfishing.admin (вся команда админская)
 * /рыбалка reload | rod [игрок] [уровень] | stats <игрок>
 */
public final class FishCommand implements CommandExecutor, TabCompleter {

    private final ZenFishing plugin;

    public FishCommand(ZenFishing plugin) { this.plugin = plugin; }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        String sub = args.length == 0 ? "" : args[0].toLowerCase(Locale.ROOT);
        switch (sub) {
            case "" -> {
                if (!(sender instanceof Player p)) { plugin.msg(sender, "players-only"); if (sender.hasPermission("zenfishing.admin")) plugin.msg(sender, "usage-admin"); return true; }
                if (!p.hasPermission("zenfishing.use")) { plugin.msg(p, "no-permission"); return true; }
                plugin.menu().openMain(p);
            }
            case "продать", "sell" -> {
                if (!(sender instanceof Player p)) { plugin.msg(sender, "players-only"); return true; }
                if (!p.hasPermission("zenfishing.use")) { plugin.msg(p, "no-permission"); return true; }
                plugin.sellAll(p);
            }
            case "топ", "top" -> top(sender);
            case "сеть", "net" -> { if (!sender.hasPermission("zenfishing.admin")) { plugin.msg(sender, "no-permission"); return true; } net(sender, args); }
            case "журнал", "journal", "book" -> {
                Player target;
                if (args.length >= 2) {
                    if (!sender.hasPermission("zenfishing.admin")) { plugin.msg(sender, "no-permission"); return true; }
                    target = Bukkit.getPlayerExact(args[1]);
                    if (target == null) { plugin.msg(sender, "player-not-found", "player", args[1]); return true; }
                } else if (sender instanceof Player p) target = p;
                else { plugin.msg(sender, "players-only"); return true; }
                if (!target.hasPermission("zenfishing.use")) { plugin.msg(sender, "no-permission"); return true; }
                if (!sender.hasPermission("zenfishing.admin") && plugin.journal().has(target)) { plugin.msg(sender, "journal-already"); return true; }
                plugin.journal().give(target);
                plugin.msg(sender, "journal-given-to", "player", target.getName());
            }
            case "reload", "rod", "stats" -> {
                if (!sender.hasPermission("zenfishing.admin")) { plugin.msg(sender, "no-permission"); return true; }
                admin(sender, sub, args);
            }
            default -> plugin.msg(sender, sender.hasPermission("zenfishing.admin") ? "usage-admin" : "usage");
        }
        return true;
    }

    private void net(CommandSender sender, String[] args) {
        Nets nets = plugin.nets();
        if (args.length >= 2 && (args[1].equalsIgnoreCase("list") || args[1].equalsIgnoreCase("clear"))) {
            if (!sender.hasPermission("zenfishing.admin")) { plugin.msg(sender, "no-permission"); return; }
            if (args[1].equalsIgnoreCase("list")) {
                if (nets.all().isEmpty()) { plugin.msg(sender, "net-list-empty"); return; }
                for (Nets.Net n : nets.all().values()) sender.sendMessage(Text.parse("&7• &f" + nets.describe(n)));
            } else {
                java.util.UUID owner = null;
                if (args.length >= 3) { OfflinePlayer t = offline(args[2]); if (t == null) { plugin.msg(sender, "player-unknown", "player", args[2]); return; } owner = t.getUniqueId(); }
                plugin.msg(sender, "net-cleared", "count", nets.removeAll(owner));
            }
            return;
        }
        if (args.length >= 2) {
            if (!sender.hasPermission("zenfishing.admin")) { plugin.msg(sender, "no-permission"); return; }
            Player target = Bukkit.getPlayerExact(args[1]);
            if (target == null) { plugin.msg(sender, "player-not-found", "player", args[1]); return; }
            nets.give(target);
            plugin.msg(sender, "net-given-to", "player", target.getName());
            return;
        }
        if (!(sender instanceof Player p)) { plugin.msg(sender, "players-only"); return; }
        if (!p.hasPermission("zenfishing.use")) { plugin.msg(p, "no-permission"); return; }
        if (!nets.enabled()) { plugin.msg(p, "net-disabled"); return; }
        nets.give(p);
        plugin.msg(p, "net-given-to", "player", p.getName());
    }

    private void admin(CommandSender sender, String sub, String[] args) {
        switch (sub) {
            case "reload" -> { plugin.reloadAll(); plugin.msg(sender, "reloaded", "fish", plugin.fish().size()); }
            case "rod" -> {
                Player target = args.length >= 2 ? Bukkit.getPlayerExact(args[1]) : sender instanceof Player p ? p : null;
                if (target == null) { plugin.msg(sender, "player-not-found", "player", args.length >= 2 ? args[1] : "?"); return; }
                int level = 1;
                if (args.length >= 3) { try { level = Integer.parseInt(args[2]); } catch (NumberFormatException e) { plugin.msg(sender, "usage-admin"); return; } }
                ItemStack rod = plugin.rods().create(level, target);
                for (ItemStack rest : target.getInventory().addItem(rod).values()) target.getWorld().dropItemNaturally(target.getLocation(), rest);
                plugin.msg(sender, "rod-given", "player", target.getName(), "level", plugin.rods().level(rod));
            }
            case "stats" -> {
                if (args.length < 2) { plugin.msg(sender, "usage-admin"); return; }
                OfflinePlayer t = offline(args[1]);
                if (t == null) { plugin.msg(sender, "player-unknown", "player", args[1]); return; }
                PlayerStats s = plugin.stats().peek(t);
                plugin.msg(sender, "stats", "player", t.getName() != null ? t.getName() : args[1], "caught", s.caught, "known", s.known(),
                        "total", plugin.fish().size(), "best", best(s), "earned", Text.num(s.earned));
            }
        }
    }

    public String best(PlayerStats s) {
        Fish f = plugin.fish().get(s.bestFish);
        return f == null ? "—" : f.rarity().color() + f.name();
    }

    private void top(CommandSender sender) {
        List<PlayerStats> all = plugin.stats().everyone();
        all.sort(Comparator.comparingInt((PlayerStats s) -> s.caught).reversed());
        plugin.msg(sender, "top-header");
        int n = 0;
        for (PlayerStats s : all) {
            if (s.caught <= 0 || ++n > 10) break;
            plugin.msg(sender, "top-line", "n", n, "player", s.name, "value", s.caught + " рыбы, видов " + s.known());
        }
    }

    private OfflinePlayer offline(String name) {
        OfflinePlayer t = Bukkit.getPlayerExact(name);
        return t != null ? t : Bukkit.getOfflinePlayerIfCached(name);
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        boolean admin = sender.hasPermission("zenfishing.admin");
        if (args.length == 1) {
            List<String> l = new ArrayList<>(List.of("продать", "топ", "журнал"));
            if (admin) l.addAll(List.of("сеть", "reload", "rod", "stats"));
            return filter(l, args[0]);
        }
        if (!admin) return List.of();
        if (args.length == 2 && (args[0].equalsIgnoreCase("rod") || args[0].equalsIgnoreCase("stats") || args[0].equalsIgnoreCase("журнал") || args[0].equalsIgnoreCase("journal"))) return filter(names(), args[1]);
        if (args.length == 2 && (args[0].equalsIgnoreCase("сеть") || args[0].equalsIgnoreCase("net"))) { List<String> l = new ArrayList<>(List.of("list", "clear")); l.addAll(names()); return filter(l, args[1]); }
        if (args.length == 3 && args[0].equalsIgnoreCase("rod")) return filter(List.of("1", "10", "25", "50"), args[2]);
        return List.of();
    }

    private List<String> names() { List<String> n = new ArrayList<>(); for (Player p : Bukkit.getOnlinePlayers()) n.add(p.getName()); return n; }

    private List<String> filter(List<String> opts, String pre) {
        List<String> out = new ArrayList<>();
        for (String o : opts) if (o.toLowerCase(Locale.ROOT).startsWith(pre.toLowerCase(Locale.ROOT))) out.add(o);
        return out;
    }
}
