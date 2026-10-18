package ink.hoka.zenquests;

import org.bukkit.Bukkit;
import org.bukkit.GameMode;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerChangedWorldEvent;
import org.bukkit.event.player.PlayerQuitEvent;

import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

/** /ffly — полёт на своей ферме для Ферма+. Своя ферма — мир TakuFarmersAPI.getFarmWorldName(uuid). */
public final class FarmFly implements CommandExecutor, Listener {

    private final ZenQuests plugin;
    private final Set<UUID> flying = new HashSet<>();

    public FarmFly(ZenQuests plugin) { this.plugin = plugin; }

    /** Имя мира фермы игрока (TakuFarmers) или null. */
    public static String farmWorld(UUID id) {
        try {
            Class<?> api = Class.forName("ink.hoka.takufarmers.api.TakuFarmersAPI");
            Object n = api.getMethod("getFarmWorldName", UUID.class).invoke(null, id);
            return n == null ? null : n.toString();
        } catch (Throwable t) { return null; }
    }

    public boolean onOwnFarm(Player p) {
        String w = farmWorld(p.getUniqueId());
        return w != null && w.equalsIgnoreCase(p.getWorld().getName());
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player p)) { plugin.msg(sender, "players-only"); return true; }
        if (!plugin.getConfig().getBoolean("ffly.enabled", true)) return true;
        if (!plugin.quests().isPremium(p) && !p.hasPermission("zenquests.ffly.free")) { plugin.msg(p, "ffly-no-premium"); return true; }
        if (!onOwnFarm(p)) { plugin.msg(p, "ffly-not-farm"); return true; }
        if (flying.remove(p.getUniqueId())) { stop(p); plugin.msg(p, "ffly-off"); return true; }
        flying.add(p.getUniqueId());
        p.setAllowFlight(true);
        plugin.msg(p, "ffly-on");
        return true;
    }

    private void stop(Player p) {
        if (p.getGameMode() == GameMode.CREATIVE || p.getGameMode() == GameMode.SPECTATOR) return;
        p.setFlying(false); p.setAllowFlight(false);
    }

    @EventHandler
    public void onWorld(PlayerChangedWorldEvent e) {
        Player p = e.getPlayer();
        if (flying.contains(p.getUniqueId()) && !onOwnFarm(p)) {
            flying.remove(p.getUniqueId()); stop(p); plugin.msg(p, "ffly-left");
        }
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) {
        if (flying.remove(e.getPlayer().getUniqueId())) stop(e.getPlayer());
    }
}
