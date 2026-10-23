package ink.hoka.noratrum;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.JoinConfiguration;
import net.kyori.adventure.text.event.ClickEvent;
import net.kyori.adventure.text.event.HoverEvent;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.format.TextColor;
import net.kyori.adventure.text.format.TextDecoration;
import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerCommandPreprocessEvent;
import org.bukkit.event.server.ServerCommandEvent;
import org.bukkit.plugin.Plugin;
import org.bukkit.plugin.PluginDescriptionFile;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Своя выдача /plugins (/pl, /bukkit:plugins): как у Paper — «Server Plugins (N)», «Paper Plugins», «Bukkit Plugins» —
 * плюс секция «Leaf Plugins» сверху (ядро Leaf). Перехватываем команду до выполнения и печатаем сами.
 * Доступно всем с правом noratrum.plugins (по умолчанию true); без него команда уходит в ваниллу.
 */
public final class PluginsCommand implements Listener {

    private static final Set<String> LABELS = Set.of("plugins", "pl", "bukkit:plugins", "bukkit:pl", "minecraft:plugins");
    private static final TextColor INFO = TextColor.color(52, 159, 218);
    private static final TextColor PAPER = TextColor.color(2, 136, 209);
    private static final TextColor BUKKIT = TextColor.color(237, 139, 0);
    private static final TextColor ENABLED = TextColor.color(85, 255, 85);
    private static final TextColor DISABLED = TextColor.color(255, 85, 85);

    private final Noratrum plugin;

    public PluginsCommand(Noratrum plugin) { this.plugin = plugin; }

    private boolean enabled() { return plugin.getConfig().getBoolean("plugins-command.enabled", true); }

    private static boolean matches(String msg) {
        String s = msg.strip();
        if (s.startsWith("/")) s = s.substring(1);
        return LABELS.contains(s.toLowerCase(Locale.ROOT));
    }

    @EventHandler(priority = EventPriority.LOWEST, ignoreCancelled = true)
    public void onPlayer(PlayerCommandPreprocessEvent e) {
        if (!enabled() || !matches(e.getMessage())) return;
        if (!e.getPlayer().hasPermission("noratrum.plugins")) return;   // право отнято — остаётся ванильная команда (ей нужен bukkit.command.plugins)
        e.setCancelled(true);
        send(e.getPlayer());
    }

    @EventHandler(priority = EventPriority.LOWEST, ignoreCancelled = true)
    public void onConsole(ServerCommandEvent e) {
        if (!enabled() || !matches(e.getCommand())) return;
        e.setCancelled(true);
        send(e.getSender());
    }

    public void send(CommandSender to) {
        Plugin[] all = Bukkit.getPluginManager().getPlugins();
        List<String> leafNames = plugin.getConfig().getStringList("plugins-command.leaf-plugins");
        List<Plugin> leaf = new ArrayList<>(), paper = new ArrayList<>(), bukkit = new ArrayList<>();
        for (Plugin p : all) {
            if (leafNames.stream().anyMatch(n -> n.equalsIgnoreCase(p.getName()))) leaf.add(p);
            else if (p.getPluginMeta() instanceof PluginDescriptionFile) bukkit.add(p);
            else paper.add(p);
        }
        Comparator<Plugin> byName = Comparator.comparing(p -> p.getName().toLowerCase(Locale.ROOT));
        leaf.sort(byName); paper.sort(byName); bukkit.sort(byName);

        Component info = Component.text("ⓘ ", INFO).hoverEvent(HoverEvent.showText(Component.text("Плагины сервера. Наведи на имя — версия и авторы, клик — /version <имя>.", NamedTextColor.WHITE)));
        to.sendMessage(info.append(Component.text("Server Plugins (" + all.length + "):", NamedTextColor.WHITE)));

        String leafHeader = plugin.getConfig().getString("plugins-command.leaf-header", "Leaf Plugins");
        TextColor leafColor = TextColor.fromHexString(plugin.getConfig().getString("plugins-command.leaf-color", "#8CF58C"));
        if (!leaf.isEmpty()) section(to, leafHeader, leafColor == null ? TextColor.color(140, 245, 140) : leafColor, leaf);
        if (!paper.isEmpty()) section(to, "Paper Plugins", PAPER, paper);
        if (!bukkit.isEmpty()) section(to, "Bukkit Plugins", BUKKIT, bukkit);
    }

    private void section(CommandSender to, String title, TextColor color, List<Plugin> list) {
        to.sendMessage(Component.text(title + " (" + list.size() + "):", color));
        List<Component> names = new ArrayList<>();
        for (Plugin p : list) names.add(name(p));
        to.sendMessage(Component.text(" - ", NamedTextColor.DARK_GRAY).append(Component.join(JoinConfiguration.separator(Component.text(", ", NamedTextColor.WHITE)), names)));
    }

    private Component name(Plugin p) {
        var meta = p.getPluginMeta();
        Component hover = Component.text("Версия: ", NamedTextColor.GRAY).append(Component.text(meta.getVersion(), NamedTextColor.WHITE));
        if (!meta.getAuthors().isEmpty()) hover = hover.append(Component.newline()).append(Component.text("Авторы: ", NamedTextColor.GRAY)).append(Component.text(String.join(", ", meta.getAuthors()), NamedTextColor.WHITE));
        if (meta.getDescription() != null && !meta.getDescription().isBlank()) hover = hover.append(Component.newline()).append(Component.text(meta.getDescription(), NamedTextColor.GREEN));   // &a
        if (!p.isEnabled()) hover = hover.append(Component.newline()).append(Component.text("Выключен", DISABLED));
        return Component.text(p.getName(), p.isEnabled() ? ENABLED : DISABLED)
                .decoration(TextDecoration.ITALIC, false)
                .hoverEvent(HoverEvent.showText(hover))
                .clickEvent(ClickEvent.suggestCommand("/version " + p.getName()));
    }
}
