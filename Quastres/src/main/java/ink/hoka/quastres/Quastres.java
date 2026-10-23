package ink.hoka.quastres;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.minimessage.MiniMessage;
import net.kyori.adventure.text.serializer.legacy.LegacyComponentSerializer;
import org.bukkit.command.CommandSender;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Quastres — полублоки сверх лимита Carpentry. Каждый полублок — одно состояние потушенного костра
 * (campfire / soul_campfire × facing × signal_fire); модель на состояние лежит в паке Nexo, предмет — Nexo-item.
 * Плагин ставит нужное состояние по ПКМ предметом, роняет предмет при ломании и не даёт состоянию измениться
 * (поджиг, готовка, сено под костром, тушение лопатой).
 */
public final class Quastres extends JavaPlugin {

    private static Quastres instance;
    private SlabRegistry slabs;
    private NexoBridge nexo;

    public static Quastres get() { return instance; }

    @Override
    public void onEnable() {
        instance = this;
        saveDefaultConfig();
        if (!new java.io.File(getDataFolder(), "blocks.yml").exists()) saveResource("blocks.yml", false);
        nexo = new NexoBridge(this);
        slabs = new SlabRegistry(this);
        slabs.load();
        getServer().getPluginManager().registerEvents(new SlabListener(this), this);
        getLogger().info("Полублоков: " + slabs.all().size() + (nexo.available() ? " (предметы — Nexo)" : " (Nexo нет — свои предметы)"));
    }

    public void reload() { reloadConfig(); slabs.load(); }

    public SlabRegistry slabs() { return slabs; }
    public NexoBridge nexo() { return nexo; }

    public static Component text(String s) {
        if (s == null) return Component.empty();
        if (s.contains("&") || s.contains("§")) return LegacyComponentSerializer.legacyAmpersand().deserialize(s.replace('§', '&'));
        return MiniMessage.miniMessage().deserialize(s);
    }

    public void msg(CommandSender to, String key, Object... kv) {
        String s = getConfig().getString("messages." + key);
        if (s == null || s.isEmpty()) return;
        for (int i = 0; i + 1 < kv.length; i += 2) s = s.replace("{" + kv[i] + "}", String.valueOf(kv[i + 1]));
        to.sendMessage(text(getConfig().getString("messages.prefix", "") + s));
    }
}
