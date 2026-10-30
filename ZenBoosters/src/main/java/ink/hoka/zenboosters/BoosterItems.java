package ink.hoka.zenboosters;

import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataContainer;
import org.bukkit.persistence.PersistentDataType;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Бустер-предмет: ПКМ активирует (личный или глобальный) и тратит 1 штуку. Параметры — в PDC: type, mult, millis, global. */
public final class BoosterItems implements Listener {

    private final ZenBoosters plugin;
    private final NamespacedKey kType, kMult, kMillis, kGlobal;

    public BoosterItems(ZenBoosters plugin) {
        this.plugin = plugin;
        kType = new NamespacedKey(plugin, "type"); kMult = new NamespacedKey(plugin, "mult");
        kMillis = new NamespacedKey(plugin, "millis"); kGlobal = new NamespacedKey(plugin, "global");
    }

    public ItemStack create(BoosterManager.Type type, double mult, long millis, boolean global, int amount) {
        var c = plugin.getConfig();
        Material mat = Material.matchMaterial(c.getString("items.material", "POPPY"));
        if (mat == null) mat = Material.POPPY;
        String tm = c.getString("items.type-material." + type.id(), "");
        if (tm != null && !tm.isBlank() && Material.matchMaterial(tm) != null) mat = Material.matchMaterial(tm);
        ItemStack it = new ItemStack(mat, Math.max(1, amount));
        ItemMeta m = it.getItemMeta();
        Object[] kv = {"type", type.name(), "mult", BoosterManager.fmt(mult), "time", BoosterManager.time(millis)};
        m.displayName(Text.parse(fill(c.getString(global ? "items.name-global" : "items.name", "{type} x{mult}"), kv)));
        List<net.kyori.adventure.text.Component> lore = new ArrayList<>();
        for (String l : c.getStringList(global ? "items.lore-global" : "items.lore")) lore.add(Text.parse(fill(l, kv)));
        m.lore(lore);
        m.addItemFlags(ItemFlag.values());
        try { m.setEnchantmentGlintOverride(global || c.getBoolean("items.glow", true)); } catch (Throwable ignored) { }
        String model = c.getString("items.model", "");
        if (model != null && !model.isBlank()) { try { m.setItemModel(NamespacedKey.fromString(model)); } catch (Throwable ignored) { } }
        PersistentDataContainer pdc = m.getPersistentDataContainer();
        pdc.set(kType, PersistentDataType.STRING, type.id()); pdc.set(kMult, PersistentDataType.DOUBLE, mult);
        pdc.set(kMillis, PersistentDataType.LONG, millis); pdc.set(kGlobal, PersistentDataType.BYTE, (byte) (global ? 1 : 0));
        it.setItemMeta(m);
        return it;
    }

    private static String fill(String s, Object... kv) { for (int i = 0; i + 1 < kv.length; i += 2) s = s.replace("{" + kv[i] + "}", String.valueOf(kv[i + 1])); return s; }

    public boolean isBooster(ItemStack it) { return it != null && it.hasItemMeta() && it.getItemMeta().getPersistentDataContainer().has(kType, PersistentDataType.STRING); }

    @EventHandler(priority = EventPriority.HIGH)
    public void onUse(PlayerInteractEvent e) {
        if (e.getAction() != Action.RIGHT_CLICK_AIR && e.getAction() != Action.RIGHT_CLICK_BLOCK) return;
        ItemStack it = e.getItem();
        if (!isBooster(it)) return;
        e.setCancelled(true);
        if (e.getHand() != EquipmentSlot.HAND) return;
        Player p = e.getPlayer();
        PersistentDataContainer pdc = it.getItemMeta().getPersistentDataContainer();
        String type = pdc.get(kType, PersistentDataType.STRING);
        double mult = pdc.getOrDefault(kMult, PersistentDataType.DOUBLE, 2.0);
        long millis = pdc.getOrDefault(kMillis, PersistentDataType.LONG, 1800000L);
        boolean global = pdc.getOrDefault(kGlobal, PersistentDataType.BYTE, (byte) 0) == 1;
        BoosterManager.Type t = plugin.manager().type(type);
        if (t == null) { plugin.msg(p, "unknown-type", "type", String.valueOf(type), "types", String.join(", ", plugin.manager().types().keySet())); return; }
        if (!global && !plugin.getConfig().getBoolean("items.allow-stack", true) && plugin.manager().multiplier(p.getUniqueId(), t.id()) > 1) { plugin.msg(p, "already-active", "type", t.name()); return; }
        it.setAmount(it.getAmount() - 1);
        if (global) { plugin.manager().addGlobal(t.id(), mult, millis, p.getName()); plugin.broadcast("global-started", "type", t.name(), "mult", BoosterManager.fmt(mult), "left", BoosterManager.time(millis), "by", p.getName()); }
        else { plugin.manager().addPersonal(p.getUniqueId(), t.id(), mult, millis, p.getName()); plugin.msg(p, "activated", "type", t.name(), "mult", BoosterManager.fmt(mult), "left", BoosterManager.time(millis)); }
        p.playSound(p.getLocation(), Sound.ENTITY_PLAYER_LEVELUP, 0.8f, 1.5f);
    }

    /** Разобрать "global" / "личный" из аргумента. */
    public static boolean parseGlobal(String s) { return s != null && (s.equalsIgnoreCase("global") || s.equalsIgnoreCase("глобал") || s.equalsIgnoreCase("всем")); }
    public static String key(String s) { return s == null ? "" : s.toLowerCase(Locale.ROOT); }
}
