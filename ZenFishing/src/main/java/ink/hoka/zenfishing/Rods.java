package ink.hoka.zenfishing;

import ink.hoka.zenfishing.util.Text;
import net.kyori.adventure.text.Component;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataContainer;
import org.bukkit.persistence.PersistentDataType;

import java.util.ArrayList;
import java.util.List;

/** Уровень и опыт удочки — в PDC предмета; бонусы считаются из уровня (rod.per-level) и подписки (premium.*). */
public final class Rods {

    /** Бонусы удочки в руке: доли (0.25 = +25%). */
    public record Bonus(int level, double luck, double bite, double dbl, double sell, double big, double xpMul) {}

    private final ZenFishing plugin;
    private final NamespacedKey kLevel, kXp;

    public Rods(ZenFishing plugin) {
        this.plugin = plugin;
        kLevel = new NamespacedKey(plugin, "level");
        kXp = new NamespacedKey(plugin, "xp");
    }

    public boolean isRod(ItemStack it) { return it != null && it.getType() == Material.FISHING_ROD; }
    public boolean isTagged(ItemStack it) { return isRod(it) && it.hasItemMeta() && it.getItemMeta().getPersistentDataContainer().has(kLevel, PersistentDataType.INTEGER); }

    public int level(ItemStack it) {
        if (!isTagged(it)) return isRod(it) ? 1 : 0;
        return Math.max(1, it.getItemMeta().getPersistentDataContainer().getOrDefault(kLevel, PersistentDataType.INTEGER, 1));
    }

    public int xp(ItemStack it) {
        if (!isTagged(it)) return 0;
        return it.getItemMeta().getPersistentDataContainer().getOrDefault(kXp, PersistentDataType.INTEGER, 0);
    }

    public int maxLevel() { return Math.max(1, plugin.getConfig().getInt("rod.max-level", 50)); }

    /** Опыт, нужный для перехода с level на level+1. */
    public int need(int level) {
        double base = plugin.getConfig().getDouble("rod.xp-base", 100), g = plugin.getConfig().getDouble("rod.xp-growth", 1.25);
        return (int) Math.round(base * Math.pow(g, level - 1));
    }

    /** Бонусы удочки (с учётом подписки игрока). Без удочки — уровень 0 и только подписка. */
    public Bonus bonus(ItemStack rod, boolean premium) {
        int lvl = level(rod);
        int n = Math.max(0, lvl - 1);
        var c = plugin.getConfig();
        double luck = n * c.getDouble("rod.per-level.luck", 0), bite = n * c.getDouble("rod.per-level.bite-speed", 0),
                dbl = n * c.getDouble("rod.per-level.double-catch", 0), sell = n * c.getDouble("rod.per-level.sell-bonus", 0),
                big = n * c.getDouble("rod.per-level.big-fish", 0), xp = 1;
        if (premium) {
            luck += c.getDouble("premium.luck", 0); bite += c.getDouble("premium.bite-speed", 0);
            dbl += c.getDouble("premium.double-catch", 0); sell += c.getDouble("premium.sell-bonus", 0);
            xp = c.getDouble("premium.xp-multiplier", 1);
        }
        return new Bonus(lvl, luck, Math.min(0.9, bite), Math.min(0.95, dbl), sell, big, xp);
    }

    /** Добавить опыт; возвращает новый уровень, если он вырос, иначе -1. Переписывает имя и описание. */
    public int addXp(Player p, ItemStack rod, int amount) {
        if (!isRod(rod)) return -1;
        int lvl = level(rod), xp = xp(rod) + Math.max(0, amount), max = maxLevel();
        boolean up = false;
        while (lvl < max && xp >= need(lvl)) { xp -= need(lvl); lvl++; up = true; }
        if (lvl >= max) xp = 0;
        write(rod, lvl, xp, p);
        return up ? lvl : -1;
    }

    /** Новая удочка заданного уровня. */
    public ItemStack create(int level, Player owner) {
        ItemStack rod = new ItemStack(Material.FISHING_ROD);
        write(rod, Math.max(1, Math.min(maxLevel(), level)), 0, owner);
        return rod;
    }

    /** Пометить удочку и обновить вид (если ещё не помечена — уровень 1). */
    public void refresh(ItemStack rod, Player p) { if (isRod(rod)) write(rod, level(rod), xp(rod), p); }

    private void write(ItemStack rod, int lvl, int xp, Player p) {
        ItemMeta m = rod.getItemMeta();
        if (m == null) return;
        PersistentDataContainer pdc = m.getPersistentDataContainer();
        pdc.set(kLevel, PersistentDataType.INTEGER, lvl);
        pdc.set(kXp, PersistentDataType.INTEGER, xp);
        boolean max = lvl >= maxLevel();
        Bonus b = bonus(rod, false);   // в описании — бонусы самой удочки, без подписки
        // bonus() читает уровень из предмета — он ещё старый, считаем вручную
        int n = Math.max(0, lvl - 1);
        var c = plugin.getConfig();
        String luck = pct(n * c.getDouble("rod.per-level.luck", 0)), bite = pct(n * c.getDouble("rod.per-level.bite-speed", 0)),
                dbl = pct(n * c.getDouble("rod.per-level.double-catch", 0)), sell = pct(n * c.getDouble("rod.per-level.sell-bonus", 0));
        String name = c.getString(max ? "rod.name-max" : "rod.name", "Удочка");
        m.displayName(Text.parse(fill(name, lvl, xp, luck, bite, dbl, sell)));
        List<Component> lore = new ArrayList<>();
        for (String l : c.getStringList(max ? "rod.lore-max" : "rod.lore")) lore.add(Text.parse(fill(l, lvl, xp, luck, bite, dbl, sell)));
        m.lore(lore);
        rod.setItemMeta(m);
    }

    private String fill(String s, int lvl, int xp, String luck, String bite, String dbl, String sell) {
        return s.replace("{level}", String.valueOf(lvl)).replace("{xp}", String.valueOf(xp)).replace("{need}", String.valueOf(need(lvl)))
                .replace("{bar}", bar(lvl, xp)).replace("{luck}", luck).replace("{bite}", bite).replace("{double}", dbl).replace("{sell}", sell);
    }

    private String bar(int lvl, int xp) {
        var c = plugin.getConfig();
        int len = c.getInt("rod.bar.length", 20);
        int filled = lvl >= maxLevel() ? len : (int) Math.round(len * Math.min(1.0, xp / (double) need(lvl)));
        return c.getString("rod.bar.filled", "&b▮").repeat(filled) + c.getString("rod.bar.empty", "&8▮").repeat(len - filled);
    }

    public static String pct(double d) { return Text.num(Math.round(d * 1000.0) / 10.0); }
}
