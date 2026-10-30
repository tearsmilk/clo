package ink.hoka.zenfishing.menu;

import ink.hoka.zenfishing.Fish;
import ink.hoka.zenfishing.PlayerStats;
import ink.hoka.zenfishing.Rods;
import ink.hoka.zenfishing.ZenFishing;
import ink.hoka.zenfishing.util.Text;
import net.kyori.adventure.key.Key;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryDragEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.inventory.meta.SkullMeta;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * /рыбалка: главное — профиль, удочка в руке, Ферма+, продажа, топ.
 * Улучшение удочки — отдельное меню (клавиша F с удочкой в руке): удочка, сведения, следующая ступень и одна кнопка «Улучшить».
 */
public final class FishMenu implements Listener {

    private static final class Holder implements InventoryHolder {
        final Map<Integer, Runnable> actions = new HashMap<>();
        Inventory inv;
        @Override public Inventory getInventory() { return inv; }
    }

    private static final int[] INNER = {
            10, 11, 12, 13, 14, 15, 16, 19, 20, 21, 22, 23, 24, 25,
            28, 29, 30, 31, 32, 33, 34, 37, 38, 39, 40, 41, 42, 43};
    private static final int ROD = 2, PROFILE = 4, PREMIUM = 6, SELL = 22, TOP = 24, CLOSE = 49;
    // меню улучшения (вертикальная плашка, колонки 1..7): удочка и кнопка на 3 слота; всё остальное — подсказки
    private static final int[] U_ROD = {12, 13, 14, 21, 22, 23, 30, 31, 32};   // большая удочка на фоне: 3x3 невидимых предмета с её подсказкой
    private static final int[] U_BUTTON = {48, 49, 50};
    private static final char SHIFT_TO_EDGE = '', SHIFT_BACK = '';

    private final ZenFishing plugin;

    public FishMenu(ZenFishing plugin) { this.plugin = plugin; }

    private String cfg(String key, String def) { return plugin.getConfig().getString("menu." + key, def); }
    private List<String> cfgList(String key) { return plugin.getConfig().getStringList("menu." + key); }
    private Material mat(String key, Material def) {
        String s = plugin.getConfig().getString("menu." + key);
        Material m = s == null ? null : Material.matchMaterial(s.trim());
        return m == null ? def : m;
    }
    private String fill(String s, Object... kv) {
        s = s.replace("{premium}", plugin.premiumName()).replace("{currency}", plugin.currency());
        for (int i = 0; i + 1 < kv.length; i += 2) s = s.replace("{" + kv[i] + "}", String.valueOf(kv[i + 1]));
        return s;
    }
    private List<String> fillAll(List<String> in, Object... kv) { List<String> o = new ArrayList<>(); for (String s : in) o.add(fill(s, kv)); return o; }

    // ── главное ──

    public void openMain(Player p) {
        Holder h = new Holder();
        Inventory inv = Bukkit.createInventory(h, 54, menuTitle("main", cfg("title", "Рыбалка")));
        h.inv = inv;
        frame(inv);
        PlayerStats st = plugin.stats().get(p);
        String best = bestText(st);
        inv.setItem(PROFILE, head(p, fill(cfg("profile.name", "{player}"), "player", p.getName()),
                fillAll(cfgList("profile.lore"), "caught", st.caught, "known", st.known(), "total", plugin.fish().size(), "best", best, "earned", Text.num(st.earned))));

        // удочка в руке
        ItemStack rod = p.getInventory().getItemInMainHand();
        if (!plugin.rods().isRod(rod)) rod = p.getInventory().getItemInOffHand();
        if (plugin.rods().isRod(rod)) {
            plugin.rods().refresh(rod, p);
            ItemStack show = rod.clone();
            ItemMeta m = show.getItemMeta();
            if (m != null) { m.addItemFlags(ItemFlag.values()); if (tooltipStyle() != null) try { m.setTooltipStyle(tooltipStyle()); } catch (Throwable ignored) { } show.setItemMeta(m); }
            inv.setItem(ROD, icon("rod", show));
        } else inv.setItem(ROD, icon("rod", item(Material.FISHING_ROD, cfg("rod.name", "Удочка"), cfgList("rod.none"), false)));

        // Ферма+ (подписка ZenQuests) — бонусы на рыбалке
        boolean prem = plugin.isPremium(p);
        List<String> lore = fillAll(cfgList(prem ? "premium.active.lore" : "premium.inactive.lore"));
        for (String perk : plugin.getConfig().getStringList("premium.perks")) lore.add(fill(perk));
        inv.setItem(PREMIUM, icon(prem ? "premium-active" : "premium-inactive",
                item(mat(prem ? "premium.active.item" : "premium.inactive.item", Material.NAUTILUS_SHELL), fill(cfg(prem ? "premium.active.name" : "premium.inactive.name", "{premium}")), lore, prem)));

        // продажа / топ
        ZenFishing.Sale sale = plugin.appraise(p);
        inv.setItem(SELL, icon("sell", item(mat("sell.item", Material.GOLD_INGOT), cfg("sell.name", "Продать"),
                fillAll(cfgList("sell.lore"), "count", sale.count(), "amount", Text.num(sale.amount())), false)));
        h.actions.put(SELL, () -> { if (plugin.sellAll(p) != null) p.playSound(p.getLocation(), Sound.ENTITY_EXPERIENCE_ORB_PICKUP, 1f, 1.2f); openMain(p); });
        inv.setItem(TOP, icon("top", item(mat("top.item", Material.WRITABLE_BOOK), cfg("top.name", "Топ"), topLore(), false)));
        inv.setItem(CLOSE, icon("close", item(mat("close.item", Material.BARRIER), cfg("close.name", "Закрыть"), List.of(), false)));
        h.actions.put(CLOSE, p::closeInventory);
        p.openInventory(inv);
    }

    private List<String> topLore() {
        List<PlayerStats> all = plugin.stats().everyone();
        List<String> out = new ArrayList<>();
        String line = cfg("top.line", "&7{n}. &f{player} &8— &f{value}");
        all.sort(Comparator.comparingInt((PlayerStats s) -> s.caught).reversed());
        out.add(cfg("top.lore-caught", "&bПо улову:"));
        int n = 0;
        for (PlayerStats s : all) { if (s.caught <= 0 || ++n > 5) break; out.add(fill(line, "n", n, "player", s.name, "value", s.caught)); }
        all.sort(Comparator.comparingInt((PlayerStats s) -> s.known()).reversed());
        out.add(""); out.add(cfg("top.lore-biggest", "&bПо видам:"));
        n = 0;
        for (PlayerStats s : all) { if (s.known() <= 0 || ++n > 5) break; out.add(fill(line, "n", n, "player", s.name, "value", s.known() + "/" + plugin.fish().size())); }
        return out;
    }

    private String bestText(PlayerStats s) {
        Fish f = plugin.fish().get(s.bestFish);
        return f == null ? "—" : f.rarity().color() + f.name();
    }

    // ── улучшение удочки (F с удочкой в руке) ──

    private ItemStack rodInHand(Player p) {
        ItemStack rod = p.getInventory().getItemInMainHand();
        if (!plugin.rods().isRod(rod)) rod = p.getInventory().getItemInOffHand();
        return plugin.rods().isRod(rod) ? rod : null;
    }

    public void openUpgrade(Player p) {
        Rods rods = plugin.rods();
        Holder h = new Holder();
        Inventory inv = Bukkit.createInventory(h, 54, menuTitle("upgrade", cfg("rod-title", "Удочка")));
        h.inv = inv;
        frame(inv);
        ItemStack rod = rodInHand(p);
        if (rod == null) {
            for (int slot : U_ROD) inv.setItem(slot, invisible(cfg("rod-none.name", "Нет удочки"), cfgList("rod-none.lore")));
            hideInventory(p);
            p.openInventory(inv);
            return;
        }
        rods.refresh(rod, p);
        ItemStack show = rod.clone();
        ItemMeta m = show.getItemMeta();
        if (m != null) { m.addItemFlags(ItemFlag.values()); if (tooltipStyle() != null) try { m.setTooltipStyle(tooltipStyle()); } catch (Throwable ignored) { } show.setItemMeta(m); }
        for (int slot : U_ROD) inv.setItem(slot, invisibleLike(show));

        boolean prem = plugin.isPremium(p);
        int lvl = rods.level(rod), tier = rods.tier(rod);
        Rods.Tier cur = rods.current(rod), next = rods.next(rod);
        double money = plugin.economy().balance(p), cost = rods.nextCost(rod, prem);
        Object[] kv = {"level", lvl, "xp", rods.xp(rod), "need", rods.need(lvl), "bar", rods.bar(lvl, rods.xp(rod)), "tier", tier, "max-tier", rods.maxTier(),
                "money", Text.num(money), "cost", Text.num(cost), "need-level", next == null ? "-" : next.level(), "next-tier", tier + 1};
        if (next == null) {
            for (int slot : U_BUTTON) inv.setItem(slot, invisible(fill(cfg("upgrade.button.name-max", "&7Улучшить"), kv), fillAll(cfgList("upgrade.button.lore-max"), kv)));
        } else {
            boolean okLevel = lvl >= next.level(), okMoney = money >= cost || cost <= 0, can = okLevel && okMoney;
            List<String> bl = fillAll(cfgList("upgrade.button.lore"), kv);
            bl.addAll(rods.bonusLines(next));
            bl.add("");
            bl.add(fill(cfg(okLevel ? "upgrade.button.req-level-ok" : "upgrade.button.req-level-no", "&7Уровень: {need-level}"), kv));
            bl.add(fill(cfg(okMoney ? "upgrade.button.req-money-ok" : "upgrade.button.req-money-no", "&7Цена: {cost}"), kv));
            bl.add("");
            bl.add(cfg(can ? "upgrade.button.hint" : "upgrade.button.hint-locked", can ? "&eНажми, чтобы улучшить" : "&cПока недоступно"));
            for (int slot : U_BUTTON) {
                inv.setItem(slot, invisible(fill(cfg(can ? "upgrade.button.name" : "upgrade.button.name-locked", "&aУлучшить"), kv), bl));
                h.actions.put(slot, () -> upgrade(p));
            }
        }
        hideInventory(p);
        p.openInventory(inv);
    }

    private void upgrade(Player p) {
        Rods rods = plugin.rods();
        ItemStack rod = rodInHand(p);
        if (rod == null) { plugin.msg(p, "upgrade-no-rod"); openUpgrade(p); return; }
        Rods.Tier next = rods.next(rod);
        if (next == null) { plugin.msg(p, "upgrade-max"); return; }
        if (rods.level(rod) < next.level()) { plugin.msg(p, "upgrade-need-level", "level", next.level()); return; }
        double cost = rods.nextCost(rod, plugin.isPremium(p));
        if (cost > 0) {
            if (!plugin.economy().canCharge()) { plugin.msg(p, "sell-unavailable"); return; }
            if (!plugin.economy().take(p, cost)) { plugin.msg(p, "upgrade-no-money", "cost", Text.num(cost)); return; }
        }
        if (!rods.upgrade(rod, p)) return;
        plugin.msg(p, "upgraded", "tier", rods.tier(rod), "max-tier", rods.maxTier(), "cost", Text.num(cost));
        p.playSound(p.getLocation(), Sound.BLOCK_ANVIL_USE, 0.6f, 1.4f);
        openUpgrade(p);
    }

    /** F (смена рук) с удочкой в главной руке — открыть меню улучшения. */
    @EventHandler
    public void onSwap(org.bukkit.event.player.PlayerSwapHandItemsEvent e) {
        if (!plugin.getConfig().getBoolean("menu.upgrade.open-on-swap", true)) return;
        Player p = e.getPlayer();
        if (!plugin.rods().isRod(p.getInventory().getItemInMainHand())) return;
        e.setCancelled(true);
        if (!p.hasPermission("zenfishing.use")) return;
        openUpgrade(p);
    }

    /**
     * Скрыть предметы игрока и ванильную рамку инвентаря на время меню: TakuFarmers (perf.ContainerSkin) умеет это пакетами
     * для своих панелей; тянемся к его экземпляру через CookManager.skin. Нет TakuFarmers — просто ничего не скрываем.
     * Вызывать ДО openInventory: ContainerSkin сам снимает скрытие при закрытии окна.
     */
    private void hideInventory(Player p) {
        if (!plugin.getConfig().getBoolean("menu.upgrade.hide-inventory", true)) return;
        try {
            org.bukkit.plugin.Plugin tf = Bukkit.getPluginManager().getPlugin("TakuFarmers");
            if (tf == null || !tf.isEnabled()) return;
            Object cooking = tf.getClass().getMethod("cooking").invoke(tf);
            if (cooking == null) return;
            java.lang.reflect.Field f = cooking.getClass().getDeclaredField("skin"); f.setAccessible(true);
            Object skin = f.get(cooking);
            if (skin == null) return;
            skin.getClass().getMethod("hideInventory", Player.class, int.class).invoke(skin, p, 54);
        } catch (Throwable t) {
            if (!hideWarned) { plugin.getLogger().warning("Не удалось скрыть инвентарь через TakuFarmers ContainerSkin: " + t); hideWarned = true; }
        }
    }
    private boolean hideWarned;

    /** Невидимый предмет с именем и описанием другого предмета (подсказка удочки на большой картинке). */
    private ItemStack invisibleLike(ItemStack src) {
        ItemStack it = new ItemStack(Material.PAPER);
        ItemMeta m = it.getItemMeta(); ItemMeta sm = src.getItemMeta();
        if (m != null && sm != null) {
            m.displayName(sm.displayName()); m.lore(sm.lore()); m.addItemFlags(ItemFlag.values());
            if (tooltipStyle() != null) try { m.setTooltipStyle(tooltipStyle()); } catch (Throwable ignored) { }
            it.setItemMeta(m);
        }
        return icon("empty", it);
    }

    /** Невидимый предмет-кнопка (модель menu.icons.empty), текст — только в подсказке; фон рисует плашка. */
    private ItemStack invisible(String name, List<String> lore) {
        ItemStack it = item(Material.PAPER, name, lore, false);
        return icon("empty", it);
    }

    // ── события ──

    @EventHandler
    public void onClick(InventoryClickEvent e) {
        if (!(e.getInventory().getHolder() instanceof Holder h)) return;
        e.setCancelled(true);
        if (e.getClickedInventory() != e.getInventory()) return;
        Runnable r = h.actions.get(e.getSlot());
        if (r != null && e.getWhoClicked() instanceof Player p) {
            p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.5f, 1.2f);
            r.run();
        }
    }

    @EventHandler
    public void onDrag(InventoryDragEvent e) { if (e.getInventory().getHolder() instanceof Holder) e.setCancelled(true); }

    // ── оформление ──

    private boolean textured() { return plugin.getConfig().getBoolean("menu.textures.enabled", false); }

    private Component menuTitle(String background, String text) {
        Component title = Text.parse(text);
        String bg = plugin.getConfig().getString("menu.textures.backgrounds." + background, "");
        if (!textured() || bg == null || bg.isEmpty()) return title;
        Key font = Key.key(plugin.getConfig().getString("menu.textures.font", "zenquests:menu"));
        String seq = plugin.getConfig().getString("menu.textures.sequences." + background, plugin.getConfig().getString("menu.textures.sequence", ""));
        if (seq == null || seq.isBlank()) seq = "" + SHIFT_TO_EDGE + "{bg}" + SHIFT_BACK;
        Component image = Component.text(seq.replace("{bg}", bg)).font(font).color(NamedTextColor.WHITE);
        if (!plugin.getConfig().getBoolean("menu.textures.title", false)) return image;
        return Component.empty().append(image).append(title);
    }

    private void frame(Inventory inv) {
        if (textured()) { inv.clear(); return; }
        ItemStack dark = item(mat("background", Material.BLACK_STAINED_GLASS_PANE), " ", List.of(), false);
        ItemStack acc = item(mat("accent", Material.LIGHT_BLUE_STAINED_GLASS_PANE), " ", List.of(), false);
        ItemStack cor = item(mat("corner", Material.CYAN_STAINED_GLASS_PANE), " ", List.of(), false);
        int rows = inv.getSize() / 9;
        for (int i = 0; i < inv.getSize(); i++) {
            int row = i / 9, col = i % 9;
            boolean edgeRow = row == 0 || row == rows - 1, edgeCol = col == 0 || col == 8;
            if (edgeRow && edgeCol) inv.setItem(i, cor);
            else if (edgeRow) inv.setItem(i, acc);
            else inv.setItem(i, dark);
        }
    }

    private ItemStack item(Material mat, String name, List<String> lore, boolean glow) { return item(new ItemStack(mat), name, lore, glow); }

    private ItemStack item(ItemStack it, String name, List<String> lore, boolean glow) {
        ItemMeta m = it.getItemMeta();
        if (m != null) {
            m.displayName(Text.parse(name));
            List<Component> l = new ArrayList<>();
            for (String s : lore) l.add(Text.parse(s));
            m.lore(l);
            m.addItemFlags(ItemFlag.values());
            if (glow) try { m.setEnchantmentGlintOverride(true); } catch (Throwable ignored) { }
            if (name.isBlank()) { try { m.setHideTooltip(true); } catch (Throwable ignored) { } }
            else if (tooltipStyle() != null) { try { m.setTooltipStyle(tooltipStyle()); } catch (Throwable ignored) { } }
            it.setItemMeta(m);
        }
        return it;
    }

    private ItemStack head(Player p, String name, List<String> lore) {
        ItemStack it = item(Material.PLAYER_HEAD, name, lore, false);
        if (it.getItemMeta() instanceof SkullMeta sm) { sm.setOwningPlayer(p); it.setItemMeta(sm); }
        return it;
    }

    /** Своя модель кнопки из menu.icons.<key> (ресурспак), если задана. */
    private ItemStack icon(String key, ItemStack it) {
        String model = plugin.getConfig().getString("menu.icons." + key, "");
        if (model == null || model.isBlank()) return it;
        ItemMeta m = it.getItemMeta();
        if (m != null) { try { m.setItemModel(NamespacedKey.fromString(model)); it.setItemMeta(m); } catch (Throwable ignored) { } }
        return it;
    }

    private NamespacedKey tooltipStyle() {
        String s = plugin.getConfig().getString("menu.tooltip-style", "");
        return s == null || s.isBlank() ? null : NamespacedKey.fromString(s);
    }
}
