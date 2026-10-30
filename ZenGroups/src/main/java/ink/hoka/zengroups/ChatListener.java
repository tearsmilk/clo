package ink.hoka.zengroups;

import ink.hoka.zengroups.util.Text;
import io.papermc.paper.event.player.AsyncChatEvent;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.serializer.plain.PlainTextComponentSerializer;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;

/** Чат с префиксом/суффиксом группы; вход/выход — применить права и вид, выгрузить кэш. */
public final class ChatListener implements Listener {

    private final ZenGroups plugin;

    public ChatListener(ZenGroups plugin) { this.plugin = plugin; }

    @EventHandler(priority = EventPriority.LOWEST)
    public void onJoin(PlayerJoinEvent e) { plugin.refresh(e.getPlayer()); }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) {
        plugin.perms().remove(e.getPlayer());
        plugin.display().remove(e.getPlayer());
        plugin.users().unload(e.getPlayer().getUniqueId());
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onChat(AsyncChatEvent e) {
        if (!plugin.getConfig().getBoolean("chat.enabled", true)) return;
        String format = plugin.getConfig().getString("chat.format", "{prefix}{name}{suffix}&7: &f{message}");
        String colorPerm = plugin.getConfig().getString("chat.color-permission", "zengroups.chat.color");
        e.renderer((source, displayName, message, viewer) -> render(source, message, format, colorPerm));
    }

    private Component render(Player p, Component message, String format, String colorPerm) {
        Group g = plugin.primary(p.getUniqueId());
        String raw = PlainTextComponentSerializer.plainText().serialize(message);
        Component msg = p.hasPermission(colorPerm) ? Text.parse(raw) : Component.text(raw);
        String[] parts = format.replace("{prefix}", g.chatPrefix()).replace("{suffix}", g.chatSuffix()).replace("{name}", p.getName()).split("\\{message}", -1);
        Component out = Text.parse(parts[0]).append(msg);
        if (parts.length > 1) out = out.append(Text.parse(parts[1]));
        return out;
    }
}
