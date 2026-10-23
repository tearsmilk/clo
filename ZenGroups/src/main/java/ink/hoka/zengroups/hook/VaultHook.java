package ink.hoka.zengroups.hook;

import ink.hoka.zengroups.Group;
import ink.hoka.zengroups.ZenGroups;
import net.milkbowl.vault.chat.Chat;
import net.milkbowl.vault.permission.Permission;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.entity.Player;
import org.bukkit.plugin.ServicePriority;

import java.util.List;
import java.util.UUID;

/** Vault: провайдер прав и чата, чтобы другие плагины видели группы и префиксы ZenGroups. */
public final class VaultHook {
    private VaultHook() {}

    public static void tryRegister(ZenGroups plugin) {
        if (Bukkit.getPluginManager().getPlugin("Vault") == null) return;
        try {
            Perm perm = new Perm(plugin);
            Bukkit.getServicesManager().register(Permission.class, perm, plugin, ServicePriority.Highest);
            Bukkit.getServicesManager().register(Chat.class, new ChatImpl(plugin, perm), plugin, ServicePriority.Highest);
            plugin.getLogger().info("Vault найден — ZenGroups зарегистрирован как провайдер прав и чата.");
        } catch (Throwable t) { plugin.getLogger().warning("Vault: " + t); }
    }

    private static UUID uuid(String name) { OfflinePlayer p = Bukkit.getOfflinePlayerIfCached(name); return p == null ? null : p.getUniqueId(); }

    static final class Perm extends Permission {
        private final ZenGroups zg;
        Perm(ZenGroups zg) { this.zg = zg; this.plugin = zg; }
        @Override public String getName() { return "ZenGroups"; }
        @Override public boolean isEnabled() { return zg.isEnabled(); }
        @Override public boolean hasSuperPermsCompat() { return true; }
        @Override public boolean hasGroupSupport() { return true; }
        @Override public boolean playerHas(String world, String player, String permission) {
            Player p = Bukkit.getPlayerExact(player);
            if (p != null) return p.hasPermission(permission);
            UUID id = uuid(player);
            return id != null && Boolean.TRUE.equals(zg.registry().effectivePerms(zg.groupsOf(id)).get(permission.toLowerCase()));
        }
        @Override public boolean playerAdd(String world, String player, String permission) { return false; }
        @Override public boolean playerRemove(String world, String player, String permission) { return false; }
        @Override public boolean groupHas(String world, String group, String permission) {
            Group g = zg.registry().get(group);
            return g != null && Boolean.TRUE.equals(zg.registry().effectivePerms(g).get(permission.toLowerCase()));
        }
        @Override public boolean groupAdd(String world, String group, String permission) { return false; }
        @Override public boolean groupRemove(String world, String group, String permission) { return false; }
        @Override public boolean playerInGroup(String world, String player, String group) {
            UUID id = uuid(player);
            if (id == null) return false;
            for (Group g : zg.groupsOf(id)) if (g.id().equalsIgnoreCase(group)) return true;
            return false;
        }
        @Override public boolean playerAddGroup(String world, String player, String group) {
            UUID id = uuid(player); Group g = zg.registry().get(group);
            if (id == null || g == null) return false;
            zg.users().add(id, g.id(), null); Player p = Bukkit.getPlayer(id); if (p != null) zg.refresh(p); return true;
        }
        @Override public boolean playerRemoveGroup(String world, String player, String group) {
            UUID id = uuid(player);
            if (id == null) return false;
            boolean ok = zg.users().take(id, group); Player p = Bukkit.getPlayer(id); if (p != null) zg.refresh(p); return ok;
        }
        @Override public String[] getPlayerGroups(String world, String player) {
            UUID id = uuid(player);
            if (id == null) return new String[0];
            List<Group> gs = zg.groupsOf(id); String[] out = new String[gs.size()];
            for (int i = 0; i < out.length; i++) out[i] = gs.get(i).id();
            return out;
        }
        @Override public String getPrimaryGroup(String world, String player) { UUID id = uuid(player); return id == null ? zg.defaultGroup() : zg.primary(id).id(); }
        @Override public String[] getGroups() { return zg.registry().all().keySet().toArray(new String[0]); }
    }

    static final class ChatImpl extends Chat {
        private final ZenGroups zg;
        ChatImpl(ZenGroups zg, Permission perm) { super(perm); this.zg = zg; }
        private Group primary(String player) { UUID id = uuid(player); return id == null ? zg.registry().get(zg.defaultGroup()) : zg.primary(id); }
        @Override public String getName() { return "ZenGroups"; }
        @Override public boolean isEnabled() { return zg.isEnabled(); }
        @Override public String getPlayerPrefix(String world, String player) { return ink.hoka.zengroups.util.Text.glyphs(primary(player).chatPrefix()); }
        @Override public void setPlayerPrefix(String world, String player, String prefix) { }
        @Override public String getPlayerSuffix(String world, String player) { return ink.hoka.zengroups.util.Text.glyphs(primary(player).chatSuffix()); }
        @Override public void setPlayerSuffix(String world, String player, String suffix) { }
        @Override public String getGroupPrefix(String world, String group) { Group g = zg.registry().get(group); return g == null ? "" : g.chatPrefix(); }
        @Override public void setGroupPrefix(String world, String group, String prefix) { }
        @Override public String getGroupSuffix(String world, String group) { Group g = zg.registry().get(group); return g == null ? "" : g.chatSuffix(); }
        @Override public void setGroupSuffix(String world, String group, String suffix) { }
        @Override public int getPlayerInfoInteger(String world, String player, String node, int def) { return def; }
        @Override public void setPlayerInfoInteger(String world, String player, String node, int value) { }
        @Override public int getGroupInfoInteger(String world, String group, String node, int def) { return def; }
        @Override public void setGroupInfoInteger(String world, String group, String node, int value) { }
        @Override public double getPlayerInfoDouble(String world, String player, String node, double def) { return def; }
        @Override public void setPlayerInfoDouble(String world, String player, String node, double value) { }
        @Override public double getGroupInfoDouble(String world, String group, String node, double def) { return def; }
        @Override public void setGroupInfoDouble(String world, String group, String node, double value) { }
        @Override public boolean getPlayerInfoBoolean(String world, String player, String node, boolean def) { return def; }
        @Override public void setPlayerInfoBoolean(String world, String player, String node, boolean value) { }
        @Override public boolean getGroupInfoBoolean(String world, String group, String node, boolean def) { return def; }
        @Override public void setGroupInfoBoolean(String world, String group, String node, boolean value) { }
        @Override public String getPlayerInfoString(String world, String player, String node, String def) { return def; }
        @Override public void setPlayerInfoString(String world, String player, String node, String value) { }
        @Override public String getGroupInfoString(String world, String group, String node, String def) { return def; }
        @Override public void setGroupInfoString(String world, String group, String node, String value) { }
    }
}
