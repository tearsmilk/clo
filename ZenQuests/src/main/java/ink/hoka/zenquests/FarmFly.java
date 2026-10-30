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

import java.util.UUID;

/** /ffly — полёт на своей ферме для Ферма+ (переключатель, помнится между заходами в PlayerData.ffly).
 *  Своя ферма — мир TakuFarmersAPI.getFarmWorldName(uuid). */
public final class FarmFly implements CommandExecutor, Listener {

    private final ZenQuests plugin;

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

    private boolean allowed(Player p) {
        return plugin.getConfig().getBoolean("ffly.enabled", true) && (plugin.quests().isPremium(p) || p.hasPermission("zenquests.ffly.free"));
    }

    /** Применить сохранённый выбор: на своей ферме с правом — разрешить полёт, иначе снять. */
    public void apply(Player p, boolean notifyLeft) {
        PlayerData d = plugin.quests().data(p);
        boolean fly = d.ffly && allowed(p) && onOwnFarm(p);
        if (fly) { if (!p.getAllowFlight()) p.setAllowFlight(true); }
        else if (d.ffly && !onOwnFarm(p)) { stop(p); if (notifyLeft) plugin.msg(p, "ffly-left"); }
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player p)) { plugin.msg(sender, "players-only"); return true; }
        if (!plugin.getConfig().getBoolean("ffly.enabled", true)) return true;
        if (!plugin.quests().isPremium(p) && !p.hasPermission("zenquests.ffly.free")) { plugin.msg(p, "ffly-no-premium"); return true; }
        if (!onOwnFarm(p)) { plugin.msg(p, "ffly-not-farm"); return true; }
        PlayerData d = plugin.quests().data(p);
        d.ffly = !d.ffly; d.dirty = true;
        if (!d.ffly) { stop(p); plugin.msg(p, "ffly-off"); return true; }
        p.setAllowFlight(true);
        plugin.msg(p, "ffly-on");
        return true;
    }

    private void stop(Player p) {
        if (p.getGameMode() == GameMode.CREATIVE || p.getGameMode() == GameMode.SPECTATOR) return;
        p.setFlying(false); p.setAllowFlight(false);
    }

    /** Сменил мир: на свою ферму — вернуть полёт (если /ffly включён), с фермы — снять, выбор не сбрасывается. */
    @EventHandler
    public void onWorld(PlayerChangedWorldEvent e) { apply(e.getPlayer(), true); }

    /** Зашёл на сервер прямо на ферме — полёт сразу, выбор /ffly хранится в данных игрока. */
    @EventHandler
    public void onJoin(org.bukkit.event.player.PlayerJoinEvent e) {
        Player p = e.getPlayer();
        Bukkit.getScheduler().runTaskLater(plugin, () -> { if (p.isOnline()) apply(p, false); }, 10L);
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) { /* выбор сохраняется в PlayerData; полёт сервер сам сбросит при входе, apply вернёт его на ферме */ }
}
