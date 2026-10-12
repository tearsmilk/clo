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

import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * /рыбалка                — меню
 * /рыбалка продать        — продать всю рыбу
 * /рыбалка топ            — топ рыбаков
 * /рыбалка reload | rod [игрок] [уровень] | stats <игрок> | premium give|take|check <игрок> [срок]
 */
public final class FishCommand implements CommandExecutor, TabCompleter {

    private static final List<String> PREMIUM = List.of("give", "take", "check");
    private static final List<String> TERMS = List.of("1d", "7d", "30d", "90d", "forever");
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
            case "reload", "rod", "stats", "premium" -> {
                if (!sender.hasPermission("zenfishing.admin")) { plugin.msg(sender, "no-permission"); return true; }
                admin(sender, sub, args);
            }
            default -> plugin.msg(sender, sender.hasPermission("zenfishing.admin") ? "usage-admin" : "usage");
        }
        return true;
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
            case "premium" -> premium(sender, args);
        }
    }

    public String best(PlayerStats s) {
        Fish f = plugin.fish().get(s.bestFish);
        return f == null ? "—" : f.rarity().color() + f.name() + " &f" + Text.num(s.bestWeight) + " кг";
    }

    private void top(CommandSender sender) {
        List<PlayerStats> all = plugin.stats().everyone();
        all.sort(Comparator.comparingInt((PlayerStats s) -> s.caught).reversed());
        plugin.msg(sender, "top-header");
        int n = 0;
        for (PlayerStats s : all) {
            if (s.caught <= 0 || ++n > 10) break;
            plugin.msg(sender, "top-line", "n", n, "player", s.name, "value", s.caught + " рыбы, рекорд " + best(s));
        }
    }

    private OfflinePlayer offline(String name) {
        OfflinePlayer t = Bukkit.getPlayerExact(name);
        return t != null ? t : Bukkit.getOfflinePlayerIfCached(name);
    }

    private void premium(CommandSender sender, String[] args) {
        if (args.length < 3 || !PREMIUM.contains(args[1].toLowerCase(Locale.ROOT))) { plugin.msg(sender, "usage-admin"); return; }
        OfflinePlayer target = offline(args[2]);
        if (target == null) { plugin.msg(sender, "player-unknown", "player", args[2]); return; }
        String name = target.getName() != null ? target.getName() : args[2];
        PremiumStore store = plugin.premium();
        switch (args[1].toLowerCase(Locale.ROOT)) {
            case "give" -> {
                Duration term;
                try { term = PremiumStore.parse(args.length >= 4 ? args[3] : null); }
                catch (IllegalArgumentException e) { plugin.msg(sender, "premium-bad-term", "term", args[3]); return; }
                long until = store.give(target.getUniqueId(), term);
                String left = left(until);
                plugin.msg(sender, "premium-given", "player", name, "time", left);
                if (target.getPlayer() != null) plugin.msg(target.getPlayer(), "premium-received", "time", left);
            }
            case "take" -> {
                if (store.take(target.getUniqueId())) {
                    plugin.msg(sender, "premium-taken", "player", name);
                    if (target.getPlayer() != null) plugin.msg(target.getPlayer(), "premium-lost");
                } else plugin.msg(sender, "premium-none", "player", name);
            }
            default -> {
                Long until = store.expires(target.getUniqueId());
                if (until != null) plugin.msg(sender, "premium-check", "player", name, "time", left(until));
                else if (target.getPlayer() != null && plugin.isPremium(target.getPlayer())) plugin.msg(sender, "premium-check-perm", "player", name);
                else plugin.msg(sender, "premium-none", "player", name);
            }
        }
    }

    public String left(long until) {
        if (until == PremiumStore.FOREVER) return plugin.getConfig().getString("messages.premium-forever", "навсегда");
        return Text.duration(Duration.ofMillis(until - System.currentTimeMillis()));
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        boolean admin = sender.hasPermission("zenfishing.admin");
        if (args.length == 1) {
            List<String> l = new ArrayList<>(List.of("продать", "топ"));
            if (admin) l.addAll(List.of("reload", "rod", "stats", "premium"));
            return filter(l, args[0]);
        }
        if (!admin) return List.of();
        if (args[0].equalsIgnoreCase("premium")) {
            if (args.length == 2) return filter(PREMIUM, args[1]);
            if (args.length == 3) return filter(names(), args[2]);
            if (args.length == 4 && args[1].equalsIgnoreCase("give")) return filter(TERMS, args[3]);
            return List.of();
        }
        if (args.length == 2 && (args[0].equalsIgnoreCase("rod") || args[0].equalsIgnoreCase("stats"))) return filter(names(), args[1]);
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
