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

/**
 * Удочка: уровень и опыт — в PDC предмета (растут от рыбалки). Улучшение — ступени rod.tiers: одна кнопка в меню (F с удочкой в руке),
 * каждая ступень требует уровень удочки и монеты Vault и даёт набор бонусов целиком. Бонусы = ступень + подписка Ферма+.
 */
public final class Rods {

    /** Бонусы удочки в руке: доли (0.25 = +25%). */
    public record Bonus(int level, double luck, double bite, double dbl, double sell, double big, double xpMul) {}

    /** Ступень улучшения: требуемый уровень удочки, цена в монетах и бонусы (накопительно — значения ступени целиком). */
    public record Tier(int level, double cost, double luck, double bite, double dbl, double sell, double xp) {}

    private final ZenFishing plugin;
    private final NamespacedKey kLevel, kXp, kTier;

    public Rods(ZenFishing plugin) {
        this.plugin = plugin;
        kLevel = new NamespacedKey(plugin, "level");
        kXp = new NamespacedKey(plugin, "xp");
        kTier = new NamespacedKey(plugin, "tier");
    }

    public boolean isRod(ItemStack it) { return it != null && it.getType() == Material.FISHING_ROD; }
    public boolean isTagged(ItemStack it) { return isRod(it) && it.hasItemMeta() && it.getItemMeta().getPersistentDataContainer().has(kLevel, PersistentDataType.INTEGER); }

    private int pdc(ItemStack it, NamespacedKey k, int def) {
        if (!isTagged(it)) return def;
        return it.getItemMeta().getPersistentDataContainer().getOrDefault(k, PersistentDataType.INTEGER, def);
    }

    public int level(ItemStack it) { return isRod(it) ? Math.max(1, pdc(it, kLevel, 1)) : 0; }
    public int xp(ItemStack it) { return pdc(it, kXp, 0); }
    public int tier(ItemStack it) { return isRod(it) ? Math.max(0, pdc(it, kTier, 0)) : 0; }
    public int maxLevel() { return Math.max(1, plugin.getConfig().getInt("rod.max-level", 50)); }

    /** Опыт, нужный для перехода с level на level+1. */
    public int need(int level) {
        double base = plugin.getConfig().getDouble("rod.xp-base", 100), g = plugin.getConfig().getDouble("rod.xp-growth", 1.25);
        return (int) Math.round(base * Math.pow(g, level - 1));
    }

    // ── ступени улучшения (rod.tiers) ──

    private List<Tier> tiers;
    public List<Tier> tiers() {
        if (tiers != null) return tiers;
        List<Tier> out = new ArrayList<>();
        for (java.util.Map<?, ?> m : plugin.getConfig().getMapList("rod.tiers")) {
            out.add(new Tier(num(m.get("level"), 1).intValue(), num(m.get("cost"), 0).doubleValue(), num(m.get("luck"), 0).doubleValue(),
                    num(m.get("bite"), 0).doubleValue(), num(m.get("double"), 0).doubleValue(), num(m.get("sell"), 0).doubleValue(), num(m.get("xp"), 0).doubleValue()));
        }
        return tiers = out;
    }
    public void reloadTiers() { tiers = null; }
    private static Number num(Object o, Number def) { return o instanceof Number n ? n : def; }
    public int maxTier() { return tiers().size(); }
    /** Ступень с номером t (1..maxTier), null — нет такой. */
    public Tier tierCfg(int t) { return t >= 1 && t <= tiers().size() ? tiers().get(t - 1) : null; }
    public Tier current(ItemStack rod) { return tierCfg(tier(rod)); }
    public Tier next(ItemStack rod) { return tierCfg(tier(rod) + 1); }
    /** Цена следующей ступени с учётом скидки Ферма+. */
    public double nextCost(ItemStack rod, boolean premium) {
        Tier n = next(rod);
        if (n == null) return 0;
        return Math.round(n.cost() * (premium ? 1 - plugin.getConfig().getDouble("premium.upgrade-discount", 0) : 1));
    }

    /** Поднять ступень на 1 (проверки уровня и денег — у вызывающего). */
    public boolean upgrade(ItemStack rod, Player p) {
        if (!isRod(rod) || next(rod) == null) return false;
        ItemMeta m = rod.getItemMeta();
        m.getPersistentDataContainer().set(kTier, PersistentDataType.INTEGER, tier(rod) + 1);
        rod.setItemMeta(m);
        refresh(rod, p);
        return true;
    }

    /** Бонусы удочки (с учётом подписки игрока). Без удочки — уровень 0 и только подписка. */
    public Bonus bonus(ItemStack rod, boolean premium) {
        double luck = 0, bite = 0, dbl = 0, sell = 0, big = 0, xp = 1;
        Tier t = isRod(rod) ? current(rod) : null;
        if (t != null) { luck = t.luck(); bite = t.bite(); dbl = t.dbl(); sell = t.sell(); xp += t.xp(); }
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
            if (l.equals("{bonuses}")) {
                Tier t = current(rod);
                if (t != null) for (String line : bonusLines(t)) lore.add(Text.parse(line));
            } else lore.add(Text.parse(fill(l, rod, lvl, xp)));
        }
        m.lore(lore);
        if (c.getBoolean("rod.unbreakable", true)) { m.setUnbreakable(true); m.addItemFlags(org.bukkit.inventory.ItemFlag.HIDE_UNBREAKABLE); }
        String tip = c.getString("rod.tooltip-style", "");
        if (tip != null && !tip.isBlank()) { try { m.setTooltipStyle(NamespacedKey.fromString(tip)); } catch (Throwable ignored) { } }
        rod.setItemMeta(m);
    }

    /** Строки бонусов ступени по шаблону rod.bonus-line (только ненулевые). */
    public List<String> bonusLines(Tier t) {
        List<String> out = new ArrayList<>();
        String tpl = plugin.getConfig().getString("rod.bonus-line", "&7{name}: &a+{value}%");
        String[][] rows = {{"luck", String.valueOf(t.luck())}, {"bite", String.valueOf(t.bite())}, {"double", String.valueOf(t.dbl())}, {"sell", String.valueOf(t.sell())}, {"xp", String.valueOf(t.xp())}};
        for (String[] r : rows) {
            double v = Double.parseDouble(r[1]);
            if (v <= 0) continue;
            out.add(tpl.replace("{name}", plugin.getConfig().getString("rod.bonus-names." + r[0], r[0])).replace("{value}", pct(v)));
        }
        return out;
    }

    private String fill(String s, ItemStack rod, int lvl, int xp) {
        return s.replace("{level}", String.valueOf(lvl)).replace("{xp}", String.valueOf(xp)).replace("{need}", String.valueOf(need(lvl)))
                .replace("{bar}", bar(lvl, xp)).replace("{tier}", String.valueOf(tier(rod))).replace("{max-tier}", String.valueOf(maxTier()));
    }

    public String bar(int lvl, int xp) {
        var c = plugin.getConfig();
        int len = c.getInt("rod.bar.length", 20);
        int filled = lvl >= maxLevel() ? len : (int) Math.round(len * Math.min(1.0, xp / (double) need(lvl)));
        return c.getString("rod.bar.filled", "&b▮").repeat(filled) + c.getString("rod.bar.empty", "&8▮").repeat(len - filled);
    }

    public static String pct(double d) { return Text.num(Math.round(d * 1000.0) / 10.0); }
}
