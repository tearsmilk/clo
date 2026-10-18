package ink.hoka.zenfishing;

import ink.hoka.zenfishing.util.Text;
import net.kyori.adventure.text.Component;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataContainer;
import org.bukkit.persistence.PersistentDataType;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Предмет-рыба: материал или предмет Nexo, подпись с весом, вид и вес — в PDC. */
public final class FishItems {

    public record Caught(Fish fish, double weight) {}

    private final ZenFishing plugin;
    private final NamespacedKey kFish, kWeight;

    public FishItems(ZenFishing plugin) {
        this.plugin = plugin;
        kFish = new NamespacedKey(plugin, "fish");
        kWeight = new NamespacedKey(plugin, "weight");
    }

    public ItemStack create(Fish f, double weight, Player who) {
        ItemStack it = base(f.item());
        ItemMeta m = it.getItemMeta();
        if (m == null) return it;
        PersistentDataContainer pdc = m.getPersistentDataContainer();
        pdc.set(kFish, PersistentDataType.STRING, f.id());
        String date = LocalDate.now().format(DateTimeFormatter.ofPattern("dd.MM.yyyy"));
        m.displayName(Text.parse(fill(plugin.getConfig().getString("catch.name", "{fish}"), f, weight, who, date)));
        List<Component> lore = new ArrayList<>();
        for (String l : plugin.getConfig().getStringList("catch.lore")) lore.add(Text.parse(fill(l, f, weight, who, date)));
        m.lore(lore);
        String model = f.model() != null ? f.model() : plugin.getConfig().getString("catch.item-model", "").replace("{id}", f.id());
        if (model != null && !model.isBlank()) { try { m.setItemModel(NamespacedKey.fromString(model)); } catch (Throwable ignored) { } }
        String tip = plugin.getConfig().getString("catch.tooltip-style", "");
        if (tip != null && !tip.isBlank()) { try { m.setTooltipStyle(NamespacedKey.fromString(tip)); } catch (Throwable ignored) { } }
        it.setItemMeta(m);
        return it;
    }

    /** Предмет-образец вида (для меню): модель как у улова, без веса. */
    public ItemStack sample(Fish f) {
        ItemStack it = base(f.item());
        ItemMeta m = it.getItemMeta();
        String model = f.model() != null ? f.model() : plugin.getConfig().getString("catch.item-model", "").replace("{id}", f.id());
        if (m != null && model != null && !model.isBlank()) { try { m.setItemModel(NamespacedKey.fromString(model)); it.setItemMeta(m); } catch (Throwable ignored) { } }
        return it;
    }

    private String fill(String s, Fish f, double w, Player who, String date) {
        return s.replace("{color}", f.rarity().color()).replace("{fish}", f.name()).replace("{rarity}", f.rarity().name())
                .replace("{weight}", Text.num(w)).replace("{price}", Text.num(Math.round(f.priceFor(w))))
                .replace("{currency}", plugin.getConfig().getString("sell.currency", ""))
                .replace("{player}", who == null ? "" : who.getName()).replace("{date}", date);
    }

    /** Рыба из предмета или null. */
    public Caught read(ItemStack it) {
        if (it == null || !it.hasItemMeta()) return null;
        PersistentDataContainer pdc = it.getItemMeta().getPersistentDataContainer();
        String id = pdc.get(kFish, PersistentDataType.STRING);
        Fish f = plugin.fish().get(id);
        if (f == null) return null;
        return new Caught(f, 0);
    }

    /** Базовый предмет: nexo:<id> через NexoItems (рефлексией) или материал. */
    public static ItemStack base(String spec) {
        if (spec != null && spec.toLowerCase(Locale.ROOT).startsWith("nexo:")) {
            try {
                Class<?> items = Class.forName("com.nexomc.nexo.api.NexoItems");
                Object builder = items.getMethod("itemFromId", String.class).invoke(null, spec.substring(5));
                if (builder != null) {
                    Object built = builder.getClass().getMethod("build").invoke(builder);
                    if (built instanceof ItemStack is) return is.clone();
                }
            } catch (Throwable t) {
                Bukkit.getLogger().warning("[ZenFishing] Nexo предмет " + spec + " не найден: " + t);
            }
            return new ItemStack(Material.COD);
        }
        Material m = spec == null ? null : Material.matchMaterial(spec.trim());
        return new ItemStack(m == null ? Material.COD : m);
    }
}
