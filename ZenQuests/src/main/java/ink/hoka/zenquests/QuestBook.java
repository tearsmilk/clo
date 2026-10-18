package ink.hoka.zenquests;

import ink.hoka.zenquests.util.Text;
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
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;

import java.util.ArrayList;
import java.util.List;

/** Книга квестов: предмет с 3D-моделью (book.model), ПКМ открывает /квесты; выдаётся при первом входе (book.give-on-join). */
public final class QuestBook implements Listener {

    private final ZenQuests plugin;
    private final NamespacedKey key;

    public QuestBook(ZenQuests plugin) { this.plugin = plugin; key = new NamespacedKey(plugin, "quest_book"); }

    public boolean enabled() { return plugin.getConfig().getBoolean("book.enabled", true); }

    public ItemStack create() {
        var c = plugin.getConfig();
        ItemStack it = new ItemStack(Material.BOOK);
        ItemMeta m = it.getItemMeta();
        m.displayName(Text.parse(c.getString("book.name", "&6📖 Книга квестов")));
        List<Component> lore = new ArrayList<>();
        for (String l : c.getStringList("book.lore")) lore.add(Text.parse(l));
        m.lore(lore);
        m.getPersistentDataContainer().set(key, PersistentDataType.BYTE, (byte) 1);
        m.addItemFlags(ItemFlag.values());
        String model = c.getString("book.model", "");
        if (model != null && !model.isBlank()) { try { m.setItemModel(NamespacedKey.fromString(model)); } catch (Throwable ignored) { } }
        String tip = c.getString("menu.tooltip-style", "");
        if (tip != null && !tip.isBlank()) { try { m.setTooltipStyle(NamespacedKey.fromString(tip)); } catch (Throwable ignored) { } }
        it.setItemMeta(m);
        return it;
    }

    public boolean isBook(ItemStack it) {
        return it != null && it.hasItemMeta() && it.getItemMeta().getPersistentDataContainer().has(key, PersistentDataType.BYTE);
    }

    public boolean has(Player p) {
        for (ItemStack it : p.getInventory().getContents()) if (isBook(it)) return true;
        return false;
    }

    /** Выдать книгу (в инвентарь или под ноги). */
    public void give(Player p) {
        for (ItemStack rest : p.getInventory().addItem(create()).values()) p.getWorld().dropItemNaturally(p.getLocation(), rest);
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent e) {
        if (!enabled() || !plugin.getConfig().getBoolean("book.give-on-join", true)) return;
        Player p = e.getPlayer();
        PlayerData d = plugin.quests().data(p);
        if (d.bookGiven) return;
        d.bookGiven = true; d.dirty = true;
        if (!has(p)) { give(p); plugin.msg(p, "book-given"); }
    }

    @EventHandler(priority = EventPriority.HIGH)
    public void onUse(PlayerInteractEvent e) {
        if (!enabled() || e.getItem() == null || !isBook(e.getItem())) return;
        if (e.getAction() != Action.RIGHT_CLICK_AIR && e.getAction() != Action.RIGHT_CLICK_BLOCK) return;
        e.setCancelled(true);
        if (e.getHand() != org.bukkit.inventory.EquipmentSlot.HAND) return;
        plugin.menu().openMain(e.getPlayer());
    }
}
