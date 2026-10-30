package ink.hoka.noratrum;

import ink.hoka.zenfishing.ZenFishing;
import ink.hoka.zengroups.ZenGroups;
import ink.hoka.zenquests.ZenQuests;
import ink.hoka.zenboosters.ZenBoosters;
import org.bukkit.Bukkit;
import org.bukkit.permissions.Permission;
import org.bukkit.permissions.PermissionDefault;
import org.bukkit.plugin.java.JavaPlugin;

import java.util.ArrayList;
import java.util.List;

/**
 * Noratrum — квесты (бывший ZenQuests), рыбалка (ZenFishing) и группы (ZenGroups) одним paper-плагином.
 * Папка plugins/Noratrum: config.yml (общий) + quests/, fishing/, groups/ (конфиги и данные модулей).
 * Порядок включения: группы → бустеры → квесты → рыбалка (рыбалка берёт Ферма+ из квестов и множители из бустеров).
 */
public final class Noratrum extends JavaPlugin {

    private static Noratrum instance;
    private final List<Module> modules = new ArrayList<>();
    private LegacyCommands commands;
    private ZenGroups groups; private ZenQuests quests; private ZenFishing fishing; private ZenBoosters boosters;

    public static Noratrum get() { return instance; }

    @Override
    public void onEnable() {
        instance = this;
        saveDefaultConfig();
        commands = new LegacyCommands(this);
        registerPermissions();

        if (getConfig().getBoolean("modules.groups", true)) modules.add(groups = new ZenGroups(this));
        if (getConfig().getBoolean("modules.boosters", true)) modules.add(boosters = new ZenBoosters(this));
        if (getConfig().getBoolean("modules.quests", true)) modules.add(quests = new ZenQuests(this));
        if (getConfig().getBoolean("modules.fishing", true)) modules.add(fishing = new ZenFishing(this));
        for (Module m : modules) {
            try { m.onEnable(); }
            catch (Throwable t) { getLogger().severe("Модуль " + m.getName() + " не включился: " + t); t.printStackTrace(); }
        }
        commands.hook();
        getServer().getPluginManager().registerEvents(new PluginsCommand(this), this);
        getLogger().info("Модули: " + modules.stream().map(Module::getName).toList());
    }

    @Override
    public void onDisable() {
        for (int i = modules.size() - 1; i >= 0; i--) {
            try { modules.get(i).onDisable(); } catch (Throwable t) { getLogger().warning("Модуль " + modules.get(i).getName() + ": " + t); }
        }
        modules.clear();
        instance = null;
    }

    LegacyCommands commands() { return commands; }
    public ZenGroups groups() { return groups; }
    public ZenQuests quests() { return quests; }
    public ZenFishing fishing() { return fishing; }
    public ZenBoosters boosters() { return boosters; }

    /** Права из бывших plugin.yml (paper-plugin.yml их не объявляет). */
    private void registerPermissions() {
        perm("zenquests.use", "Открывать меню квестов", PermissionDefault.TRUE);
        perm("zenquests.admin", "/квесты reload, reset, progress и premium", PermissionDefault.OP);
        perm("zenquests.ffly.free", "/ffly без подписки Ферма+", PermissionDefault.FALSE);
        perm("zenquests.premium", "Подписка Ферма+ (доп. квесты и бонусные награды)", PermissionDefault.FALSE);
        perm("zenfishing.use", "Меню рыбалки и продажа рыбы", PermissionDefault.TRUE);
        perm("zenfishing.admin", "/рыбалка reload, rod, stats, сети", PermissionDefault.OP);
        perm("zengroups.admin", "Команды /group", PermissionDefault.OP);
        perm("zenboosters.admin", "Команды /бустер", PermissionDefault.OP);
        perm("noratrum.plugins", "Видеть /plugins и /pl в выдаче Noratrum (секция Leaf). Отнять — вернётся ванильная команда", PermissionDefault.TRUE);
    }

    private void perm(String name, String desc, PermissionDefault def) {
        if (Bukkit.getPluginManager().getPermission(name) == null) Bukkit.getPluginManager().addPermission(new Permission(name, desc, def));
    }
}
