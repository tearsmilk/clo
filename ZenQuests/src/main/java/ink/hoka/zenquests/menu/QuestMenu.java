package ink.hoka.zenquests.menu;

import ink.hoka.zenquests.QuestManager;
import ink.hoka.zenquests.QuestRegistry;
import ink.hoka.zenquests.ZenQuests;
import ink.hoka.zenquests.model.Category;
import ink.hoka.zenquests.model.Quest;
import ink.hoka.zenquests.util.Text;
import net.kyori.adventure.text.Component;
import org.bukkit.Bukkit;
import org.bukkit.Material;
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

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Меню /квесты. Главное: 4 категории. Категория: квесты с прогрессом;
 * клик по выполненному — забрать награду.
 */
public final class QuestMenu implements Listener {

    /** Владелец инвентаря: какая страница открыта и какой квест в каком слоте. */
    private static final class Holder implements InventoryHolder {
        final Category category;                       // null — главное меню
        final Map<Integer, QuestManager.Entry> slots = new HashMap<>();
        final Map<Integer, Category> catSlots = new HashMap<>();
        Inventory inv;
        Holder(Category c) { category = c; }
        @Override public Inventory getInventory() { return inv; }
    }

    private static final int[] CAT_SLOTS = {10, 12, 14, 16};
    private static final int BACK_SLOT = 49;
    private static final int PREMIUM_SLOT_MAIN = 22;

    private final ZenQuests plugin;

    public QuestMenu(ZenQuests plugin) { this.plugin = plugin; }

    private String gui(String key, Object... kv) {
        String s = plugin.getConfig().getString("gui." + key, "");
        for (int i = 0; i + 1 < kv.length; i += 2) s = s.replace("{" + kv[i] + "}", String.valueOf(kv[i + 1]));
        return s;
    }

    private String catName(Category c) {
        return plugin.getConfig().getString("menu.categories." + c.key + ".name", c.key);
    }

    private Material catIcon(Category c) {
        Material m = Material.matchMaterial(plugin.getConfig().getString("menu.categories." + c.key + ".icon", "PAPER"));
        return m == null ? Material.PAPER : m;
    }

    // ── главное меню ──

    public void openMain(Player p) {
        QuestManager qm = plugin.quests();
        qm.refresh(p, false);
        Holder h = new Holder(null);
        Inventory inv = Bukkit.createInventory(h, 27, Text.parse(plugin.getConfig().getString("menu.title", "Квесты")));
        h.inv = inv;
        fill(inv);

        Category[] cats = Category.values();
        for (int i = 0; i < cats.length; i++) {
            Category c = cats[i];
            List<QuestManager.Entry> es = qm.entries(p, c);
            List<String> lore = new ArrayList<>();
            if (c == Category.STORY) {
                int chains = (int) plugin.registry().chains().values().stream()
                        .filter(ch -> !ch.premium() || qm.isPremium(p)).count();
                lore.add(gui("done-count", "done", chains - es.size(), "total", chains));
            } else {
                long done = es.stream().filter(e -> qm.isClaimed(p, e)).count();
                lore.add(gui("done-count", "done", done, "total", es.size()));
            }
            long ready = es.stream().filter(e -> qm.isDone(p, e) && !qm.isClaimed(p, e)).count();
            if (ready > 0) lore.add(gui("status-ready"));
            switch (c) {
                case DAILY -> lore.add(gui("resets-in", "time", fmt(qm.untilDailyReset())));
                case WEEKLY -> lore.add(gui("resets-in", "time", fmt(qm.untilWeeklyReset())));
                case SEASONAL -> {
                    QuestRegistry.Season s = plugin.registry().activeSeason(qm.today());
                    if (s == null) lore.add(gui("no-season"));
                    else { lore.add(s.name()); lore.add(gui("season-ends-in", "time", fmt(qm.untilSeasonEnd(s)))); }
                }
                default -> { }
            }
            inv.setItem(CAT_SLOTS[i], item(catIcon(c), catName(c), lore, ready > 0));
            h.catSlots.put(CAT_SLOTS[i], c);
        }
        inv.setItem(PREMIUM_SLOT_MAIN, premiumInfo(p));
        p.openInventory(inv);
    }

    // ── категория ──

    public void openCategory(Player p, Category c) {
        QuestManager qm = plugin.quests();
        qm.refresh(p, false);
        Holder h = new Holder(c);
        Inventory inv = Bukkit.createInventory(h, 54, Text.parse(catName(c)));
        h.inv = inv;
        fill(inv);

        List<QuestManager.Entry> es = qm.entries(p, c);
        int slot = 10;
        for (QuestManager.Entry e : es) {
            while (slot < 44 && (slot % 9 == 0 || slot % 9 == 8)) slot++;   // рамка по краям
            if (slot >= 44) break;
            inv.setItem(slot, questItem(p, e));
            h.slots.put(slot, e);
            slot++;
        }
        // без подписки — замок «ещё N заданий с Ферма+»
        int locked = lockedCount(p, c);
        if (locked > 0 && slot < 44) {
            while (slot < 44 && (slot % 9 == 0 || slot % 9 == 8)) slot++;
            if (slot < 44) {
                List<String> lore = new ArrayList<>();
                for (String l : plugin.getConfig().getStringList("premium.locked-lore")) lore.add(l.replace("{count}", String.valueOf(locked)));
                inv.setItem(slot, item(lockedIcon(), premiumText("premium.locked-name", "count", locked), lore, false));
                slot++;
            }
        }
        if (es.isEmpty() && locked == 0) {
            String text = c == Category.SEASONAL && plugin.registry().activeSeason(qm.today()) == null
                    ? gui("no-season") : gui("empty");
            inv.setItem(22, item(Material.BARRIER, text, List.of(), false));
        }
        // сюжет: пройденные цепочки тоже показываем
        if (c == Category.STORY) {
            for (QuestRegistry.Chain ch : plugin.registry().chains().values()) {
                if (ch.premium() && !qm.isPremium(p)) continue;
                int step = qm.data(p).storyStep.getOrDefault(ch.id(), 0);
                if (step < ch.steps().size()) continue;
                while (slot < 44 && (slot % 9 == 0 || slot % 9 == 8)) slot++;
                if (slot >= 44) break;
                inv.setItem(slot, item(ch.icon(), ch.name(), List.of(gui("story-done")), false));
                slot++;
            }
        }
        inv.setItem(BACK_SLOT, item(Material.ARROW, gui("back"), List.of(), false));
        p.openInventory(inv);
    }

    private ItemStack questItem(Player p, QuestManager.Entry e) {
        QuestManager qm = plugin.quests();
        Quest q = e.quest();
        int prog = qm.data(p).get(e.key());
        boolean done = prog >= q.amount(), claimed = qm.isClaimed(p, e);

        List<String> lore = new ArrayList<>();
        if (e.chain() != null) {
            QuestRegistry.Chain ch = plugin.registry().chains().get(e.chain());
            lore.add(ch.name());
            lore.add(gui("story-step", "step", ch.steps().indexOf(q) + 1, "total", ch.steps().size()));
        }
        if (q.premium()) lore.add(premiumText("premium.quest-tag"));
        lore.addAll(q.description());
        lore.add("");
        lore.add(gui("status-progress", "bar", bar(prog, q.amount()), "progress", prog, "amount", q.amount()));
        if (!q.rewardLines().isEmpty()) {
            lore.add("");
            lore.add(gui("rewards-title"));
            lore.addAll(q.rewardLines());
        }
        if (!q.premiumLines().isEmpty()) {
            lore.add("");
            boolean prem = qm.isPremium(p);
            lore.add(premiumText(prem ? "premium.bonus-title" : "premium.bonus-title-locked"));
            for (String l : q.premiumLines()) lore.add(prem ? l : "&8" + Text.strip(l));
        }
        if (claimed || done) { lore.add(""); lore.add(claimed ? gui("status-claimed") : gui("status-ready")); }
        Material icon = claimed ? Material.LIME_STAINED_GLASS_PANE : q.icon();
        return item(icon, q.name(), lore, done && !claimed);
    }

    // ── Ферма+ ──

    private String premiumText(String path, Object... kv) {
        String s = plugin.getConfig().getString(path, "");
        s = s.replace("{premium}", plugin.getConfig().getString("premium.name", "&6Ферма+"));
        for (int i = 0; i + 1 < kv.length; i += 2) s = s.replace("{" + kv[i] + "}", String.valueOf(kv[i + 1]));
        return s;
    }

    private Material lockedIcon() {
        Material m = Material.matchMaterial(plugin.getConfig().getString("premium.locked-icon", "GOLD_BLOCK"));
        return m == null ? Material.GOLD_BLOCK : m;
    }

    /** Сколько заданий в категории скрыто без подписки. */
    private int lockedCount(Player p, Category c) {
        QuestManager qm = plugin.quests();
        if (qm.isPremium(p)) return 0;
        var d = qm.data(p);
        var reg = plugin.registry();
        return switch (c) {
            case DAILY -> d.dailyPremium.size();
            case WEEKLY -> d.weeklyPremium.size();
            case SEASONAL -> {
                QuestRegistry.Season s = reg.activeSeason(qm.today());
                yield s == null ? 0 : (int) s.quests().stream().filter(Quest::premium).count();
            }
            case STORY -> (int) reg.chains().values().stream().filter(QuestRegistry.Chain::premium).count();
        };
    }

    private ItemStack premiumInfo(Player p) {
        boolean prem = plugin.quests().isPremium(p);
        String base = prem ? "premium.info-active" : "premium.info-inactive";
        Material m = Material.matchMaterial(plugin.getConfig().getString(base + ".icon", prem ? "GOLDEN_HOE" : "WHEAT"));
        List<String> lore = new ArrayList<>();
        for (String l : plugin.getConfig().getStringList(base + ".lore")) lore.add(l.replace("{premium}", plugin.getConfig().getString("premium.name", "&6Ферма+")));
        return item(m == null ? Material.WHEAT : m, premiumText(base + ".name"), lore, prem);
    }

    // ── клики ──

    @EventHandler
    public void onClick(InventoryClickEvent e) {
        if (!(e.getInventory().getHolder() instanceof Holder h)) return;
        e.setCancelled(true);
        if (!(e.getWhoClicked() instanceof Player p)) return;
        if (e.getClickedInventory() == null || !(e.getClickedInventory().getHolder() instanceof Holder)) return;
        int slot = e.getSlot();

        if (h.category == null) {
            Category c = h.catSlots.get(slot);
            if (c != null) openCategory(p, c);
            return;
        }
        if (slot == BACK_SLOT) { openMain(p); return; }
        QuestManager.Entry entry = h.slots.get(slot);
        if (entry == null) return;
        plugin.quests().claim(p, entry);
        openCategory(p, h.category);   // перерисовать (сюжет мог перейти на следующий шаг)
    }

    @EventHandler
    public void onDrag(InventoryDragEvent e) {
        if (e.getInventory().getHolder() instanceof Holder) e.setCancelled(true);
    }

    // ── помощники ──

    private void fill(Inventory inv) {
        ItemStack pane = item(Material.GRAY_STAINED_GLASS_PANE, " ", List.of(), false);
        for (int i = 0; i < inv.getSize(); i++) inv.setItem(i, pane);
        // середину — пустой
        for (int i = 0; i < inv.getSize(); i++) {
            int col = i % 9, row = i / 9;
            if (row > 0 && row < inv.getSize() / 9 - 1 && col > 0 && col < 8) inv.setItem(i, null);
        }
    }

    private ItemStack item(Material mat, String name, List<String> lore, boolean glow) {
        ItemStack it = new ItemStack(mat);
        ItemMeta m = it.getItemMeta();
        if (m != null) {
            m.displayName(Text.parse(name));
            List<Component> l = new ArrayList<>();
            for (String s : lore) l.add(Text.parse(s));
            m.lore(l);
            m.addItemFlags(ItemFlag.values());
            if (glow) {
                try { m.setEnchantmentGlintOverride(true); } catch (Throwable ignored) { }
            }
            it.setItemMeta(m);
        }
        return it;
    }

    /** Полоска из 10 квадратиков: заполненные — зелёные. */
    private String bar(int v, int max) {
        int filled = (int) Math.round(10.0 * v / Math.max(1, max));
        return "&a" + "■".repeat(Math.max(0, filled)) + "&8" + "■".repeat(Math.max(0, 10 - filled));
    }

    private String fmt(Duration d) {
        long m = Math.max(0, d.toMinutes());
        long days = m / 1440, hours = (m % 1440) / 60, mins = m % 60;
        if (days > 0) return days + " д " + hours + " ч";
        if (hours > 0) return hours + " ч " + mins + " мин";
        return mins + " мин";
    }
}
