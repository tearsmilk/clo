package ink.hoka.zenfishing;

import ink.hoka.zenfishing.util.Text;
import net.kyori.adventure.text.Component;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataContainer;
import org.bukkit.persistence.PersistentDataType;

import java.util.ArrayList;
import java.util.List;

/**
 * Удочка: уровень и опыт — в PDC предмета. Каждый уровень даёт очки прокачки (rod.points-per-level),
 * очки вкладываются в ветки (rod.upgrades.*) в меню /рыбалка → Прокачка. Бонусы считаются из веток + подписки.
 */
public final class Rods {

    /** Ветки прокачки — ключи rod.upgrades.<id>, порядок — порядок в меню. */
    public static final String[] TRACKS = {"luck", "bite", "double", "sell", "xp"};

    /** Бонусы удочки в руке: доли (0.25 = +25%). */
    public record Bonus(int level, double luck, double bite, double dbl, double sell, double big, double xpMul) {}

    private final ZenFishing plugin;
    private final NamespacedKey kLevel, kXp;
    private final NamespacedKey[] kTrack = new NamespacedKey[TRACKS.length];

    public Rods(ZenFishing plugin) {
        this.plugin = plugin;
        kLevel = new NamespacedKey(plugin, "level");
        kXp = new NamespacedKey(plugin, "xp");
        for (int i = 0; i < TRACKS.length; i++) kTrack[i] = new NamespacedKey(plugin, "up_" + TRACKS[i]);
    }

    public boolean isRod(ItemStack it) { return it != null && it.getType() == Material.FISHING_ROD; }
    public boolean isTagged(ItemStack it) { return isRod(it) && it.hasItemMeta() && it.getItemMeta().getPersistentDataContainer().has(kLevel, PersistentDataType.INTEGER); }

    private int pdc(ItemStack it, NamespacedKey k, int def) {
        if (!isTagged(it)) return def;
        return it.getItemMeta().getPersistentDataContainer().getOrDefault(k, PersistentDataType.INTEGER, def);
    }

    public int level(ItemStack it) { return isRod(it) ? Math.max(1, pdc(it, kLevel, 1)) : 0; }
    public int xp(ItemStack it) { return pdc(it, kXp, 0); }
    public int track(ItemStack it, int i) { return pdc(it, kTrack[i], 0); }
    public int maxLevel() { return Math.max(1, plugin.getConfig().getInt("rod.max-level", 50)); }
    public int pointsPerLevel() { return Math.max(1, plugin.getConfig().getInt("rod.points-per-level", 1)); }

    /** Опыт, нужный для перехода с level на level+1. */
    public int need(int level) {
        double base = plugin.getConfig().getDouble("rod.xp-base", 100), g = plugin.getConfig().getDouble("rod.xp-growth", 1.25);
        return (int) Math.round(base * Math.pow(g, level - 1));
    }

    // ── ветки ──

    private ConfigurationSection up(int i) { return plugin.getConfig().getConfigurationSection("rod.upgrades." + TRACKS[i]); }
    public String trackName(int i) { ConfigurationSection s = up(i); return s == null ? TRACKS[i] : s.getString("name", TRACKS[i]); }
    public int trackMax(int i) { ConfigurationSection s = up(i); return s == null ? 10 : s.getInt("max", 10); }
    public double trackStep(int i) { ConfigurationSection s = up(i); return s == null ? 0 : s.getDouble("per-point", 0); }
    public double trackValue(ItemStack rod, int i) { return track(rod, i) * trackStep(i); }

    /** Цена в монетах следующего улучшения ветки (0 — бесплатно). */
    public double trackCost(ItemStack rod, int i, boolean premium) {
        ConfigurationSection s = up(i);
        if (s == null) return 0;
        double c = s.getDouble("cost-base", 0) * Math.pow(s.getDouble("cost-growth", 1), track(rod, i));
        if (premium) c *= 1 - plugin.getConfig().getDouble("premium.upgrade-discount", 0);
        return Math.round(c);
    }

    public int spent(ItemStack rod) { int s = 0; for (int i = 0; i < TRACKS.length; i++) s += track(rod, i); return s; }
    public int points(ItemStack rod) { return isRod(rod) ? Math.max(0, (level(rod) - 1) * pointsPerLevel() - spent(rod)) : 0; }

    /** Вложить очко в ветку (деньги списывает вызывающий). @return false — нет очков или ветка на максимуме. */
    public boolean upgrade(ItemStack rod, int i, Player p) {
        if (!isRod(rod) || points(rod) <= 0 || track(rod, i) >= trackMax(i)) return false;
        ItemMeta m = rod.getItemMeta();
        m.getPersistentDataContainer().set(kTrack[i], PersistentDataType.INTEGER, track(rod, i) + 1);
        rod.setItemMeta(m);
        refresh(rod, p);
        return true;
    }

    /** Бонусы удочки (с учётом подписки игрока). Без удочки — уровень 0 и только подписка. */
    public Bonus bonus(ItemStack rod, boolean premium) {
        double luck = 0, bite = 0, dbl = 0, sell = 0, big = 0, xp = 1;
        if (isRod(rod)) { luck = trackValue(rod, 0); bite = trackValue(rod, 1); dbl = trackValue(rod, 2); sell = trackValue(rod, 3); xp += trackValue(rod, 4); }
        var c = plugin.getConfig();
        if (premium) {
            luck += c.getDouble("premium.luck", 0); bite += c.getDouble("premium.bite-speed", 0);
            dbl += c.getDouble("premium.double-catch", 0); sell += c.getDouble("premium.sell-bonus", 0);
            xp *= c.getDouble("premium.xp-multiplier", 1);
        }
        return new Bonus(level(rod), luck, Math.min(0.9, bite), Math.min(0.95, dbl), sell, big, xp);
    }

    /** Добавить опыт; возвращает новый уровень, если он вырос, иначе -1. */
    public int addXp(Player p, ItemStack rod, int amount) {
        if (!isRod(rod)) return -1;
        int lvl = level(rod), xp = xp(rod) + Math.max(0, amount), max = maxLevel();
        boolean up = false;
        while (lvl < max && xp >= need(lvl)) { xp -= need(lvl); lvl++; up = true; }
        if (lvl >= max) xp = 0;
        write(rod, lvl, xp, p);
        return up ? lvl : -1;
    }

    public ItemStack create(int level, Player owner) {
        ItemStack rod = new ItemStack(Material.FISHING_ROD);
        write(rod, Math.max(1, Math.min(maxLevel(), level)), 0, owner);
        return rod;
    }

    public void refresh(ItemStack rod, Player p) { if (isRod(rod)) write(rod, level(rod), xp(rod), p); }

    private void write(ItemStack rod, int lvl, int xp, Player p) {
        ItemMeta m = rod.getItemMeta();
        if (m == null) return;
        PersistentDataContainer pdc = m.getPersistentDataContainer();
        pdc.set(kLevel, PersistentDataType.INTEGER, lvl);
        pdc.set(kXp, PersistentDataType.INTEGER, xp);
        rod.setItemMeta(m);
        m = rod.getItemMeta();
        boolean max = lvl >= maxLevel();
        var c = plugin.getConfig();
        m.displayName(Text.parse(fill(c.getString(max ? "rod.name-max" : "rod.name", "Удочка"), rod, lvl, xp)));
        List<Component> lore = new ArrayList<>();
        for (String l : c.getStringList(max ? "rod.lore-max" : "rod.lore")) {
            if (l.equals("{tracks}")) {
                for (int i = 0; i < TRACKS.length; i++) if (track(rod, i) > 0)
                    lore.add(Text.parse(fill(c.getString("rod.track-line", "&7{track}: &a+{value}%"), rod, lvl, xp)
                            .replace("{track}", trackName(i)).replace("{value}", pct(trackValue(rod, i))).replace("{points}", String.valueOf(track(rod, i)))));
            } else lore.add(Text.parse(fill(l, rod, lvl, xp)));
        }
        m.lore(lore);
        if (c.getBoolean("rod.unbreakable", true)) { m.setUnbreakable(true); m.addItemFlags(org.bukkit.inventory.ItemFlag.HIDE_UNBREAKABLE); }
        String tip = c.getString("rod.tooltip-style", "");
        if (tip != null && !tip.isBlank()) { try { m.setTooltipStyle(NamespacedKey.fromString(tip)); } catch (Throwable ignored) { } }
        rod.setItemMeta(m);
    }

    private String fill(String s, ItemStack rod, int lvl, int xp) {
        return s.replace("{level}", String.valueOf(lvl)).replace("{xp}", String.valueOf(xp)).replace("{need}", String.valueOf(need(lvl)))
                .replace("{bar}", bar(lvl, xp)).replace("{free}", String.valueOf(points(rod)));
    }

    public String bar(int lvl, int xp) {
        var c = plugin.getConfig();
        int len = c.getInt("rod.bar.length", 20);
        int filled = lvl >= maxLevel() ? len : (int) Math.round(len * Math.min(1.0, xp / (double) need(lvl)));
        return c.getString("rod.bar.filled", "&b▮").repeat(filled) + c.getString("rod.bar.empty", "&8▮").repeat(len - filled);
    }

    public static String pct(double d) { return Text.num(Math.round(d * 1000.0) / 10.0); }
}
