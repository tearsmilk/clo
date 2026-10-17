package ink.hoka.zenquests;

import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import ink.hoka.zenquests.model.ObjectiveType;
import ink.hoka.zenquests.util.Text;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * /квесты              — открыть меню
 * /квесты reload       — перезагрузить config.yml и quests.yml
 * /квесты reset <игрок> [daily|weekly|seasonal|story|all] — сбросить прогресс
 * /квесты progress <игрок> <тип> [цель] [кол-во] — засчитать действие (для консоли и других плагинов)
 * /квесты premium give <игрок> [срок] — выдать подписку (30d, 12h, 1w, forever; продлевает текущую)
 * /квесты premium take <игрок>        — забрать выданную подписку
 * /квесты premium check <игрок>       — сколько осталось
 */
public final class QuestCommand implements CommandExecutor, TabCompleter {

    private static final List<String> WHAT = List.of("daily", "weekly", "seasonal", "story", "all");
    private static final List<String> PREMIUM = List.of("give", "take", "check");
    private static final List<String> TERMS = List.of("1d", "7d", "30d", "90d", "forever");
    private final ZenQuests plugin;

    public QuestCommand(ZenQuests plugin) { this.plugin = plugin; }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (args.length == 0) {
            if (!(sender instanceof Player p)) {
                plugin.msg(sender, "players-only");
                if (sender.hasPermission("zenquests.admin")) plugin.msg(sender, "usage-admin");
                return true;
            }
            if (!p.hasPermission("zenquests.use")) { plugin.msg(p, "no-permission"); return true; }
            plugin.menu().openMain(p);
            return true;
        }

        if (!sender.hasPermission("zenquests.admin")) { plugin.msg(sender, "no-permission"); return true; }
        switch (args[0].toLowerCase(Locale.ROOT)) {
            case "reload" -> {
                plugin.reloadAll();
                plugin.msg(sender, "reloaded");
            }
            case "reset" -> {
                if (args.length < 2) { plugin.msg(sender, "usage-admin"); return true; }
                Player target = Bukkit.getPlayerExact(args[1]);
                if (target == null) { plugin.msg(sender, "player-not-found", "player", args[1]); return true; }
                String what = args.length >= 3 ? args[2].toLowerCase(Locale.ROOT) : "all";
                if (!WHAT.contains(what)) { plugin.msg(sender, "usage-admin"); return true; }
                plugin.quests().reset(target, what);
                plugin.msg(sender, "reset", "player", target.getName(), "what", what);
            }
            case "progress" -> {
                // /квесты progress <игрок> <тип> [цель|-] [кол-во]
                if (args.length < 3) { plugin.msg(sender, "usage-admin"); return true; }
                Player target = Bukkit.getPlayerExact(args[1]);
                if (target == null) { plugin.msg(sender, "player-not-found", "player", args[1]); return true; }
                ObjectiveType type = ObjectiveType.parse(args[2]);
                if (type == null) { plugin.msg(sender, "unknown-type", "type", args[2]); return true; }
                String what = args.length >= 4 && !args[3].equals("-") ? args[3] : null;
                int amount = 1;
                if (args.length >= 5) {
                    try { amount = Integer.parseInt(args[4]); } catch (NumberFormatException e) { plugin.msg(sender, "usage-admin"); return true; }
                }
                plugin.quests().progress(target, type, what, amount);
                if (!(sender instanceof org.bukkit.command.ConsoleCommandSender))
                    plugin.msg(sender, "progress-added", "player", target.getName(), "type", type.name(), "amount", amount);
            }
            case "premium" -> premium(sender, args);
            default -> plugin.msg(sender, "usage-admin");
        }
        return true;
    }

    /** /квесты premium give|take|check <игрок> [срок] — работает и для игроков не в сети (если уже заходили). */
    private void premium(CommandSender sender, String[] args) {
        if (args.length < 3 || !PREMIUM.contains(args[1].toLowerCase(Locale.ROOT))) { plugin.msg(sender, "usage-admin"); return; }
        OfflinePlayer target = Bukkit.getPlayerExact(args[2]);
        if (target == null) target = Bukkit.getOfflinePlayerIfCached(args[2]);
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
                else if (target.getPlayer() != null && plugin.quests().isPremium(target.getPlayer()))
                    plugin.msg(sender, "premium-check-perm", "player", name);
                else plugin.msg(sender, "premium-none", "player", name);
            }
        }
    }

    private String left(long until) {
        if (until == PremiumStore.FOREVER) return plugin.getConfig().getString("messages.premium-forever", "навсегда");
        return Text.duration(Duration.ofMillis(until - System.currentTimeMillis()));
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (!sender.hasPermission("zenquests.admin")) return List.of();
        if (args.length == 1) return filter(List.of("reload", "reset", "progress", "premium"), args[0]);
        if (args[0].equalsIgnoreCase("premium")) {
            if (args.length == 2) return filter(PREMIUM, args[1]);
            if (args.length == 3) {
                List<String> names = new ArrayList<>();
                for (Player p : Bukkit.getOnlinePlayers()) names.add(p.getName());
                return filter(names, args[2]);
            }
            if (args.length == 4 && args[1].equalsIgnoreCase("give")) return filter(TERMS, args[3]);
            return List.of();
        }
        if (args.length == 3 && args[0].equalsIgnoreCase("progress")) {
            List<String> types = new ArrayList<>();
            for (ObjectiveType t : ObjectiveType.values()) types.add(t.name());
            return filter(types, args[2]);
        }
        if (args.length == 2 && (args[0].equalsIgnoreCase("reset") || args[0].equalsIgnoreCase("progress"))) {
            List<String> names = new ArrayList<>();
            for (Player p : Bukkit.getOnlinePlayers()) names.add(p.getName());
            return filter(names, args[1]);
        }
        if (args.length == 3 && args[0].equalsIgnoreCase("reset")) return filter(WHAT, args[2]);
        return List.of();
    }

    private List<String> filter(List<String> opts, String pre) {
        List<String> out = new ArrayList<>();
        for (String o : opts) if (o.toLowerCase(Locale.ROOT).startsWith(pre.toLowerCase(Locale.ROOT))) out.add(o);
        return out;
    }
}
