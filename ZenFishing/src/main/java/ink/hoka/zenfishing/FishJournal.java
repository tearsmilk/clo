package ink.hoka.zenfishing;

import ink.hoka.zenfishing.util.Text;
import net.kyori.adventure.text.Component;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;

import java.util.ArrayList;
import java.util.List;

/** Рыбацкий журнал: предмет с 3D-моделью (journal.model), ПКМ открывает меню рыбалки; выдаётся при первом входе (journal.give-on-join). */
public final class FishJournal implements Listener {

    private final ZenFishing plugin;
    private final NamespacedKey key;

    public FishJournal(ZenFishing plugin) { this.plugin = plugin; key = new NamespacedKey(plugin, "fish_journal"); }

    public boolean enabled() { return plugin.getConfig().getBoolean("journal.enabled", true); }

    public ItemStack create() {
        var c = plugin.getConfig();
        ItemStack it = new ItemStack(Material.BOOK);
        ItemMeta m = it.getItemMeta();
        m.displayName(Text.parse(c.getString("journal.name", "&b📘 Рыбацкий журнал")));
        List<Component> lore = new ArrayList<>();
        for (String l : c.getStringList("journal.lore")) lore.add(Text.parse(l));
        m.lore(lore);
        m.getPersistentDataContainer().set(key, PersistentDataType.BYTE, (byte) 1);
        m.addItemFlags(ItemFlag.values());
        String model = c.getString("journal.model", "");
        if (model != null && !model.isBlank()) { try { m.setItemModel(NamespacedKey.fromString(model)); } catch (Throwable ignored) { } }
        String tip = c.getString("menu.tooltip-style", "");
        if (tip != null && !tip.isBlank()) { try { m.setTooltipStyle(NamespacedKey.fromString(tip)); } catch (Throwable ignored) { } }
        it.setItemMeta(m);
        return it;
    }

    public boolean isJournal(ItemStack it) {
        return it != null && it.hasItemMeta() && it.getItemMeta().getPersistentDataContainer().has(key, PersistentDataType.BYTE);
    }

    public boolean has(Player p) {
        for (ItemStack it : p.getInventory().getContents()) if (isJournal(it)) return true;
        return false;
    }

    /** Выдать журнал (в инвентарь или под ноги). */
    public void give(Player p) {
        for (ItemStack rest : p.getInventory().addItem(create()).values()) p.getWorld().dropItemNaturally(p.getLocation(), rest);
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent e) {
        if (!enabled() || !plugin.getConfig().getBoolean("journal.give-on-join", true)) return;
        Player p = e.getPlayer();
        PlayerStats s = plugin.stats().get(p);
        if (s.journalGiven) return;
        s.journalGiven = true; s.dirty = true;
        if (!has(p)) { give(p); plugin.msg(p, "journal-given"); }
    }

    @EventHandler(priority = EventPriority.HIGH)
    public void onUse(PlayerInteractEvent e) {
        if (!enabled() || e.getItem() == null || !isJournal(e.getItem())) return;
        if (e.getAction() != Action.RIGHT_CLICK_AIR && e.getAction() != Action.RIGHT_CLICK_BLOCK) return;
        e.setCancelled(true);
        if (e.getHand() != EquipmentSlot.HAND) return;
        Player p = e.getPlayer();
        if (!p.hasPermission("zenfishing.use")) { plugin.msg(p, "no-permission"); return; }
        plugin.menu().openMain(p);
    }
}
