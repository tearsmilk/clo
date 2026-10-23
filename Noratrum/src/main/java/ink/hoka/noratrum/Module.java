package ink.hoka.noratrum;

import io.papermc.paper.plugin.configuration.PluginMeta;
import io.papermc.paper.plugin.lifecycle.event.LifecycleEventManager;
import net.kyori.adventure.text.logger.slf4j.ComponentLogger;
import org.bukkit.Server;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.generator.BiomeProvider;
import org.bukkit.generator.ChunkGenerator;
import org.bukkit.plugin.Plugin;
import org.bukkit.plugin.PluginDescriptionFile;
import org.bukkit.plugin.PluginLoader;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.List;
import java.util.logging.Logger;

/**
 * Модуль Noratrum — бывший отдельный плагин (ZenQuests, ZenFishing, ZenGroups). Реализует {@link Plugin}, чтобы старый код
 * (регистрация слушателей, планировщик, Vault, NamespacedKey) работал без правок, но:
 *   • своя папка данных (plugins/Noratrum/<папка>; старая plugins/<Имя> переносится туда при первом запуске);
 *   • своё имя → NamespacedKey(module, …) даёт прежний неймспейс (zenquests:…, zenfishing:…) — предметы с PDC не ломаются;
 *   • свой config.yml с дефолтами из ресурсов jar (<имя в нижнем регистре>/config.yml);
 *   • команды регистрируются через Brigadier хост-плагина ({@link #registerCommand}).
 * Всё, что касается самого плагина (isEnabled, lifecycle, meta), делегируется в {@link Noratrum}.
 */
public abstract class Module implements Plugin {

    private final Noratrum host;
    private final String name;
    private final File dataFolder;
    private final Logger logger;
    private FileConfiguration config;
    private boolean naggable = true;

    /** @param name имя модуля (= прежнее имя плагина, даёт неймспейс ключей), @param folder подпапка в plugins/Noratrum */
    protected Module(Noratrum host, String name, String folder) {
        this.host = host;
        this.name = name;
        this.dataFolder = new File(host.getDataFolder(), folder);
        this.logger = new ModuleLogger(host.getLogger(), name);
        migrate(new File(host.getDataFolder().getParentFile(), name));
    }

    /** Первый запуск после объединения: plugins/<СтароеИмя> → plugins/Noratrum/<folder> (конфиги, данные игроков). */
    private void migrate(File old) {
        if (dataFolder.exists() || !old.isDirectory()) return;
        try {
            Files.createDirectories(dataFolder.toPath().getParent());
            Files.move(old.toPath(), dataFolder.toPath());
            logger.info("Папка " + old.getName() + " перенесена в " + dataFolder.getPath());
        } catch (IOException e) { logger.severe("Не удалось перенести " + old.getPath() + " → " + dataFolder.getPath() + ": " + e.getMessage()); }
    }

    public Noratrum host() { return host; }

    /** Зарегистрировать команду старого образца (CommandExecutor + TabCompleter) через Brigadier хоста. */
    protected void registerCommand(String name, List<String> aliases, CommandExecutor executor, TabCompleter completer) {
        host.commands().register(name, aliases, executor, completer);
    }

    // ── конфиги и ресурсы (как у JavaPlugin, но ресурсы лежат в подпапке jar) ──

    private String resourcePath(String file) { return name.toLowerCase(java.util.Locale.ROOT) + "/" + file.replace('\\', '/'); }

    @Override public @NotNull File getDataFolder() { return dataFolder; }
    @Override public @NotNull Path getDataPath() { return dataFolder.toPath(); }

    @Override public @NotNull FileConfiguration getConfig() {
        if (config == null) reloadConfig();
        return config;
    }

    @Override public void reloadConfig() {
        config = YamlConfiguration.loadConfiguration(new File(dataFolder, "config.yml"));
        InputStream def = getResource("config.yml");
        if (def != null) config.setDefaults(YamlConfiguration.loadConfiguration(new InputStreamReader(def, StandardCharsets.UTF_8)));
    }

    @Override public void saveConfig() {
        try { getConfig().save(new File(dataFolder, "config.yml")); }
        catch (IOException e) { logger.severe("Не сохранился config.yml: " + e.getMessage()); }
    }

    @Override public void saveDefaultConfig() {
        if (!new File(dataFolder, "config.yml").exists()) saveResource("config.yml", false);
    }

    @Override public void saveResource(@NotNull String resourcePath, boolean replace) {
        InputStream in = getResource(resourcePath);
        if (in == null) { logger.warning("Нет ресурса " + resourcePath + " в jar"); return; }
        File out = new File(dataFolder, resourcePath);
        if (out.exists() && !replace) return;
        try {
            Files.createDirectories(out.toPath().getParent());
            Files.copy(in, out.toPath(), StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException e) { logger.severe("Не сохранился " + resourcePath + ": " + e.getMessage()); }
    }

    @Override public @Nullable InputStream getResource(@NotNull String filename) {
        return host.getClass().getClassLoader().getResourceAsStream(resourcePath(filename));
    }

    // ── жизненный цикл модуля ──

    @Override public void onLoad() { }
    @Override public abstract void onEnable();
    @Override public abstract void onDisable();

    // ── делегаты в хост ──

    @Override public @NotNull String getName() { return name; }
    /** Неймспейс ключей (NamespacedKey(plugin, …)) — как у JavaPlugin: имя в нижнем регистре → zenquests:…, zenfishing:… */
    @Override public @NotNull String namespace() { return name.toLowerCase(java.util.Locale.ROOT); }
    @Override public @NotNull Server getServer() { return host.getServer(); }
    @Override public boolean isEnabled() { return host.isEnabled(); }
    @Override public @NotNull Logger getLogger() { return logger; }
    @Override public @NotNull ComponentLogger getComponentLogger() { return host.getComponentLogger(); }
    @Override public @NotNull PluginMeta getPluginMeta() { return host.getPluginMeta(); }
    @SuppressWarnings("deprecation") @Override public @NotNull PluginDescriptionFile getDescription() { return host.getDescription(); }
    @SuppressWarnings("deprecation") @Override public @NotNull PluginLoader getPluginLoader() { return host.getPluginLoader(); }
    @Override public @NotNull LifecycleEventManager<Plugin> getLifecycleManager() { return host.getLifecycleManager(); }
    @Override public boolean isNaggable() { return naggable; }
    @Override public void setNaggable(boolean canNag) { naggable = canNag; }
    @Override public @Nullable ChunkGenerator getDefaultWorldGenerator(@NotNull String worldName, @Nullable String id) { return null; }
    @Override public @Nullable BiomeProvider getDefaultBiomeProvider(@NotNull String worldName, @Nullable String id) { return null; }
    @Override public boolean onCommand(@NotNull CommandSender sender, @NotNull Command command, @NotNull String label, @NotNull String[] args) { return false; }
    @Override public @Nullable List<String> onTabComplete(@NotNull CommandSender sender, @NotNull Command command, @NotNull String alias, @NotNull String[] args) { return null; }

    @Override public String toString() { return name + " (Noratrum)"; }

    /** Логгер модуля: имя Noratrum.<Модуль> — в консоли видно [Noratrum.ZenQuests]. */
    private static final class ModuleLogger extends Logger {
        private final Logger parent;
        ModuleLogger(Logger parent, String name) { super(parent.getName() + "." + name, null); this.parent = parent; setParent(parent); setLevel(parent.getLevel()); }
        @Override public void log(@NotNull java.util.logging.LogRecord r) { parent.log(r); }
    }
}
