package ink.hoka.zengroups;

import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.permissions.Permission;
import org.bukkit.permissions.PermissionAttachment;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/** Права через PermissionAttachment: пересчитываются при входе и любой смене групп. «*» — все известные серверу права. */
public final class PermissionManager {

    private final ZenGroups plugin;
    private final Map<UUID, PermissionAttachment> attachments = new HashMap<>();

    public PermissionManager(ZenGroups plugin) { this.plugin = plugin; }

    public void apply(Player p) {
        PermissionAttachment at = attachments.get(p.getUniqueId());
        if (at == null) { at = p.addAttachment(plugin); attachments.put(p.getUniqueId(), at); }
        for (String k : new java.util.ArrayList<>(at.getPermissions().keySet())) at.unsetPermission(k);
        Map<String, Boolean> perms = plugin.registry().effectivePerms(plugin.groupsOf(p.getUniqueId()));
        if (Boolean.TRUE.equals(perms.get("*"))) {
            for (Permission perm : Bukkit.getPluginManager().getPermissions()) at.setPermission(perm.getName(), true);
            perms.remove("*");
        }
        for (Map.Entry<String, Boolean> e : perms.entrySet()) at.setPermission(e.getKey(), e.getValue());
        p.updateCommands();
    }

    public void remove(Player p) {
        PermissionAttachment at = attachments.remove(p.getUniqueId());
        if (at != null) try { p.removeAttachment(at); } catch (IllegalArgumentException ignored) { }
    }

    public void applyAll() { for (Player p : Bukkit.getOnlinePlayers()) apply(p); }
}
