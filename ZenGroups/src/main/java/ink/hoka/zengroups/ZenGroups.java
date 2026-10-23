package ink.hoka.zengroups;

import ink.hoka.zengroups.util.Text;
import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import ink.hoka.noratrum.Module;
import ink.hoka.noratrum.Noratrum;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

/** Группы и права: groups.yml (группы, префиксы), permissions.yml (права), config.yml (плагин). /group add|set|take. */
public final class ZenGroups extends Module {

    public ZenGroups(Noratrum host) { super(host, "ZenGroups", "groups"); }

    private GroupRegistry registry;
    private UserStore users;
    private PermissionManager perms;
    private DisplayManager display;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        for (String f : List.of("groups.yml", "permissions.yml")) if (!new File(getDataFolder(), f).exists()) saveResource(f, false);
        registry = new GroupRegistry(this); registry.load();
        users = new UserStore(this);
        perms = new PermissionManager(this);
        display = new DisplayManager(this);
        getServer().getPluginManager().registerEvents(new ChatListener(this), this);
        ink.hoka.zengroups.hook.VaultHook.tryRegister(this);
        ink.hoka.zengroups.hook.PapiHook.tryRegister(this);
        GroupCommand gc = new GroupCommand(this);
        registerCommand("group", java.util.List.of("группа", "zengroups", "zg"), gc, gc);
        long period = 20L * Math.max(5, getConfig().getInt("expire-check-seconds", 30));
        Bukkit.getScheduler().runTaskTimer(this, this::checkExpired, period, period);
        for (Player p : Bukkit.getOnlinePlayers()) refresh(p);
        getLogger().info("Групп: " + registry.size());
    }

    @Override
    public void onDisable() { for (Player p : Bukkit.getOnlinePlayers()) { perms.remove(p); } }

    public void reloadAll() {
        reloadConfig(); registry.load();
        for (Player p : Bukkit.getOnlinePlayers()) refresh(p);
    }

    public GroupRegistry registry() { return registry; }
    public UserStore users() { return users; }
    public PermissionManager perms() { return perms; }
    public DisplayManager display() { return display; }
    public String defaultGroup() { return getConfig().getString("default-group", "default").toLowerCase(Locale.ROOT); }

    /** Активные группы игрока (+ группа по умолчанию), по убыванию веса. */
    public List<Group> groupsOf(UUID id) {
        List<Group> out = new ArrayList<>();
        for (UserStore.Entry e : users.entries(id, null)) { Group g = registry.get(e.group); if (g != null && !out.contains(g)) out.add(g); }
        Group def = registry.get(defaultGroup());
        if (def != null && !out.contains(def)) out.add(def);
        out.sort((a, b) -> Integer.compare(b.weight(), a.weight()));
        return out;
    }

    /** Главная группа — с наибольшим весом. */
    public Group primary(UUID id) { return groupsOf(id).get(0); }

    /** Пересчитать права и вид игрока после смены групп. */
    public void refresh(Player p) { perms.apply(p); display.apply(p); }

    private void checkExpired() {
        for (Player p : Bukkit.getOnlinePlayers()) {
            List<UserStore.Entry> expired = new ArrayList<>();
            users.entries(p.getUniqueId(), expired);
            if (expired.isEmpty()) continue;
            for (UserStore.Entry e : expired) msg(p, "expired", "group", displayOf(e.group));
            refresh(p);
        }
    }

    public String displayOf(String id) { Group g = registry.get(id); return g == null ? id : g.display(); }

    public void msg(CommandSender to, String key, Object... kv) {
        String s = getConfig().getString("messages." + key);
        if (s == null || s.isEmpty()) return;
        for (int i = 0; i + 1 < kv.length; i += 2) s = s.replace("{" + kv[i] + "}", String.valueOf(kv[i + 1]));
        String prefix = getConfig().getString("messages.prefix", "");
        for (String line : s.split("\n")) to.sendMessage(Text.parse(prefix + line));
    }
}
