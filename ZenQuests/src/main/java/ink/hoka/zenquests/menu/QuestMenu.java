package ink.hoka.zenquests.menu;

import ink.hoka.zenquests.PremiumStore;
import ink.hoka.zenquests.QuestManager;
import ink.hoka.zenquests.QuestRegistry;
import ink.hoka.zenquests.ZenQuests;
import ink.hoka.zenquests.model.Category;
import ink.hoka.zenquests.model.ObjectiveType;
import ink.hoka.zenquests.model.Quest;
import ink.hoka.zenquests.util.Text;
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

import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Меню /квесты.
 *   Главное — профиль игрока, 4 категории с индикаторами, Ферма+.
 *   Категория — квесты с прогрессом (по страницам), клик по выполненному — забрать награду.
 *   Сюжет — список цепочек; клик по цепочке — все её шаги: пройденные, текущий и закрытые.
 */
public final class QuestMenu implements Listener {

    /** Владелец инвентаря: что делать при клике по слоту. */
    private static final class Holder implements InventoryHolder {
        final Map<Integer, Runnable> actions = new HashMap<>();
        final Map<Integer, Runnable> rightActions = new HashMap<>();   // ПКМ: закрепить/открепить в худе
        Inventory inv;
        @Override public Inventory getInventory() { return inv; }
    }

    /** Слоты под содержимое страницы: 4 ряда по 7 внутри рамки. */
    private static final int[] INNER = {
            10, 11, 12, 13, 14, 15, 16,
            19, 20, 21, 22, 23, 24, 25,
            28, 29, 30, 31, 32, 33, 34,
            37, 38, 39, 40, 41, 42, 43};
    private static final int[] CAT_SLOTS = {19, 21, 23, 25};
    private static final int HEADER = 4, PREV = 48, BACK = 49, NEXT = 50;
    private static final int PROFILE = 4, PREMIUM_MAIN = 48, CLOSE = 50;

    private final ZenQuests plugin;

    public QuestMenu(ZenQuests plugin) { this.plugin = plugin; }

    // ── тексты из config.yml ──

    private String gui(String key, Object... kv) {
        return fill(plugin.getConfig().getString("gui." + key, ""), kv);
    }

    private List<String> guiList(String key, Object... kv) {
        List<String> out = new ArrayList<>();
        for (String l : plugin.getConfig().getStringList("gui." + key)) out.add(fill(l, kv));
        return out;
    }

    private String fill(String s, Object... kv) {
        s = s.replace("{premium}", plugin.getConfig().getString("premium.name", "&6Ферма+"));
        for (int i = 0; i + 1 < kv.length; i += 2) s = s.replace("{" + kv[i] + "}", String.valueOf(kv[i + 1]));
        return s;
    }

    private String premiumText(String path, Object... kv) {
        return fill(plugin.getConfig().getString(path, ""), kv);
    }

    private String catName(Category c) {
        return plugin.getConfig().getString("menu.categories." + c.key + ".name", c.key);
    }

    private Material catMat(Category c, String field, Material def) {
        return mat(plugin.getConfig().getString("menu.categories." + c.key + "." + field), def);
    }

    private Material mat(String name, Material def) {
        if (name == null) return def;
        Material m = Material.matchMaterial(name.trim());
        return m == null ? def : m;
    }

    // ── главное меню ──

    public void openMain(Player p) {
        QuestManager qm = plugin.quests();
        qm.refresh(p, false);
        Holder h = new Holder();
        Inventory inv = Bukkit.createInventory(h, 54, menuTitle("main", plugin.getConfig().getString("menu.title", "Квесты")));
        h.inv = inv;
        frame(inv, mat(plugin.getConfig().getString("menu.accent"), Material.LIGHT_BLUE_STAINED_GLASS_PANE),
                mat(plugin.getConfig().getString("menu.corner"), Material.CYAN_STAINED_GLASS_PANE));

        ItemStack bg = item(mat(plugin.getConfig().getString("menu.background"), Material.BLACK_STAINED_GLASS_PANE), " ", List.of(), false, 1);
        if (!textured()) for (int slot : INNER) inv.setItem(slot, bg);

        int readyAll = 0;
        Category[] cats = Category.values();
        for (int i = 0; i < cats.length && i < CAT_SLOTS.length; i++) {
            Category c = cats[i];
            List<String> lore = new ArrayList<>(plugin.getConfig().getStringList("menu.categories." + c.key + ".description"));
            if (!lore.isEmpty()) lore.add("");
            int done, total, ready;
            if (c == Category.STORY) {
                List<QuestRegistry.Chain> chains = visibleChains(p);
                total = chains.size();
                done = (int) chains.stream().filter(ch -> step(p, ch) >= ch.steps().size()).count();
                ready = (int) qm.entries(p, c).stream().filter(e -> qm.isDone(p, e)).count();
                lore.add(gui("chains-count", "done", done, "total", total));
            } else {
                List<QuestManager.Entry> es = qm.entries(p, c);
                total = es.size();
                done = (int) es.stream().filter(e -> qm.isClaimed(p, e)).count();
                ready = (int) es.stream().filter(e -> qm.isDone(p, e) && !qm.isClaimed(p, e)).count();
                lore.add(gui("done-count", "done", done, "total", total));
            }
            lore.add(bar(done, total) + " &f" + percent(done, total) + "%");
            switch (c) {
                case DAILY -> lore.add(gui("resets-in", "time", fmt(qm.untilDailyReset())));
                case WEEKLY -> lore.add(gui("resets-in", "time", fmt(qm.untilWeeklyReset())));
                case SEASONAL -> {
                    QuestRegistry.Season s = plugin.registry().activeSeason(qm.today());
                    if (s == null) lore.add(gui("no-season"));
                    else { lore.add(gui("season-name", "season", s.name())); lore.add(gui("season-ends-in", "time", fmt(qm.untilSeasonEnd(s)))); }
                }
                default -> { }
            }
            lore.add("");
            if (ready > 0) lore.add(gui("ready-count", "count", ready));
            lore.add(gui("click-open"));
            readyAll += ready;

            int slot = CAT_SLOTS[i];
            inv.setItem(slot, icon(c.key, item(catMat(c, "icon", Material.PAPER), catName(c), lore, ready > 0, Math.max(1, Math.min(64, ready)))));
            h.actions.put(slot, () -> { click(p); openCategory(p, c, 0); });

            // индикатор под категорией: есть награды / в процессе / всё сделано (на нарисованном фоне не нужен —
            // готовые награды и так видны по свечению и числу на иконке)
            if (textured()) continue;
            String state = ready > 0 ? "ready" : total > 0 && done >= total ? "done" : total == 0 ? "empty" : "progress";
            Material ind = mat(plugin.getConfig().getString("gui.indicator." + state + ".icon"), Material.GRAY_STAINED_GLASS_PANE);
            inv.setItem(slot + 9, item(ind, gui("indicator." + state + ".name"), List.of(), false, 1));
            h.actions.put(slot + 9, () -> { click(p); openCategory(p, c, 0); });
        }

        inv.setItem(PROFILE, profile(p, readyAll));
        inv.setItem(PREMIUM_MAIN, premiumInfo(p));
        inv.setItem(CLOSE, icon("close", item(Material.BARRIER, gui("close"), List.of(), false, 1)));
        h.actions.put(CLOSE, () -> { click(p); p.closeInventory(); });
        p.openInventory(inv);
    }

    private ItemStack profile(Player p, int ready) {
        QuestManager qm = plugin.quests();
        int stepsDone = 0, stepsTotal = 0;
        for (QuestRegistry.Chain ch : visibleChains(p)) {
            stepsTotal += ch.steps().size();
            stepsDone += Math.min(step(p, ch), ch.steps().size());
        }
        boolean prem = qm.isPremium(p);
        List<String> lore = guiList("profile.lore",
                "ready", ready,
                "story", stepsDone, "story_total", stepsTotal,
                "story_bar", bar(stepsDone, stepsTotal),
                "premium_state", gui(prem ? "profile.premium-on" : "profile.premium-off"));
        ItemStack it = item(Material.PLAYER_HEAD, gui("profile.name", "player", p.getName()), lore, ready > 0, 1);
        if (it.getItemMeta() instanceof SkullMeta sm) {
            sm.setOwningPlayer(p);
            it.setItemMeta(sm);
        }
        return it;
    }

    // ── категория ──

    public void openCategory(Player p, Category c) { openCategory(p, c, 0); }

    public void openCategory(Player p, Category c, int page) {
        if (c == Category.STORY) { openStory(p, page); return; }
        QuestManager qm = plugin.quests();
        qm.refresh(p, false);

        List<QuestManager.Entry> es = new ArrayList<>(qm.entries(p, c));
        // сначала готовые к награде, потом в процессе, в конце — уже полученные
        es.sort(Comparator.comparingInt(e -> qm.isClaimed(p, e) ? 2 : qm.isDone(p, e) ? 0 : 1));

        List<Runnable> placers = new ArrayList<>();
        List<Runnable> pins = new ArrayList<>();
        List<ItemStack> items = new ArrayList<>();
        for (QuestManager.Entry e : es) {
            items.add(questItem(p, e, null));
            placers.add(() -> {
                if (qm.isClaimed(p, e)) { deny(p); return; }
                if (!qm.isDone(p, e)) { deny(p); qm.claim(p, e); return; }   // claim пишет «ещё N из M»
                qm.claim(p, e);
                openCategory(p, c, page);
            });
            pins.add(qm.isClaimed(p, e) ? null : () -> { click(p); qm.togglePin(p, e); openCategory(p, c, page); });
        }
        int locked = lockedCount(p, c);
        if (locked > 0) {
            List<String> lore = new ArrayList<>();
            for (String l : plugin.getConfig().getStringList("premium.locked-lore")) lore.add(fill(l, "count", locked));
            items.add(icon("locked", item(lockedIcon(), premiumText("premium.locked-name", "count", locked), lore, false, Math.min(64, locked))));
            placers.add(() -> deny(p));
        }

        Holder h = new Holder();
        int pages = Math.max(1, (items.size() + INNER.length - 1) / INNER.length);
        int pg = Math.max(0, Math.min(page, pages - 1));
        Inventory inv = Bukkit.createInventory(h, 54, menuTitle(c.key, title(catName(c), pg, pages)));
        h.inv = inv;
        frame(inv, catMat(c, "pane", Material.GRAY_STAINED_GLASS_PANE), catMat(c, "corner", Material.BLACK_STAINED_GLASS_PANE));

        inv.setItem(HEADER, categoryHeader(p, c, es));
        place(h, items, placers, pins, pg);
        if (items.isEmpty()) {
            String text = c == Category.SEASONAL && plugin.registry().activeSeason(qm.today()) == null ? gui("no-season") : gui("empty");
            inv.setItem(22, icon("empty", item(Material.BARRIER, text, List.of(), false, 1)));
        }
        nav(h, p, pg, pages, np -> openCategory(p, c, np), () -> openMain(p));
        p.openInventory(inv);
    }

    private ItemStack categoryHeader(Player p, Category c, List<QuestManager.Entry> es) {
        QuestManager qm = plugin.quests();
        List<String> lore = new ArrayList<>(plugin.getConfig().getStringList("menu.categories." + c.key + ".description"));
        if (!lore.isEmpty()) lore.add("");
        int done = (int) es.stream().filter(e -> qm.isClaimed(p, e)).count();
        lore.add(gui("done-count", "done", done, "total", es.size()));
        lore.add(bar(done, es.size()) + " &f" + percent(done, es.size()) + "%");
        switch (c) {
            case DAILY -> lore.add(gui("resets-in", "time", fmt(qm.untilDailyReset())));
            case WEEKLY -> lore.add(gui("resets-in", "time", fmt(qm.untilWeeklyReset())));
            case SEASONAL -> {
                QuestRegistry.Season s = plugin.registry().activeSeason(qm.today());
                if (s != null) { lore.add(gui("season-name", "season", s.name())); lore.add(gui("season-ends-in", "time", fmt(qm.untilSeasonEnd(s)))); }
            }
            default -> { }
        }
        return icon(c.key, item(catMat(c, "icon", Material.PAPER), catName(c), lore, false, 1));
    }

    // ── сюжет: список цепочек ──

    public void openStory(Player p, int page) {
        QuestManager qm = plugin.quests();
        qm.refresh(p, false);
        boolean prem = qm.isPremium(p);

        List<ItemStack> items = new ArrayList<>();
        List<Runnable> placers = new ArrayList<>();
        for (QuestRegistry.Chain ch : plugin.registry().chains().values()) {
            boolean locked = ch.premium() && !prem;
            int step = Math.min(step(p, ch), ch.steps().size()), total = ch.steps().size();
            boolean finished = step >= total;
            QuestManager.Entry cur = finished ? null : entry(ch, step);
            boolean ready = cur != null && !locked && qm.isDone(p, cur);

            List<String> lore = new ArrayList<>();
            if (ch.premium()) lore.add(premiumText("premium.chain-tag"));
            lore.addAll(ch.description());
            if (!ch.description().isEmpty()) lore.add("");
            lore.add(gui("story-step", "step", Math.min(step + (finished ? 0 : 1), total), "total", total));
            lore.add(bar(step, total) + " &f" + percent(step, total) + "%");
            if (cur != null && !locked) lore.add(gui("story-current", "quest", cur.quest().name()));
            lore.add("");
            if (locked) {
                for (String l : plugin.getConfig().getStringList("premium.chain-locked-lore")) lore.add(fill(l));
            } else if (finished) lore.add(gui("story-done"));
            else if (ready) lore.add(gui("story-ready"));
            lore.add(gui("click-open-chain"));

            Material icon = locked ? lockedIcon() : ch.icon();
            String name = locked ? gui("story-locked-name", "chain", Text.strip(ch.name())) : ch.name();
            items.add(locked ? icon("locked", item(icon, name, lore, ready, 1)) : item(icon, name, lore, ready, 1));
            placers.add(() -> { click(p); openChain(p, ch.id(), 0); });
        }

        Holder h = new Holder();
        int pages = Math.max(1, (items.size() + INNER.length - 1) / INNER.length);
        int pg = Math.max(0, Math.min(page, pages - 1));
        Inventory inv = Bukkit.createInventory(h, 54, menuTitle("story", title(catName(Category.STORY), pg, pages)));
        h.inv = inv;
        frame(inv, catMat(Category.STORY, "pane", Material.PURPLE_STAINED_GLASS_PANE),
                catMat(Category.STORY, "corner", Material.MAGENTA_STAINED_GLASS_PANE));

        List<QuestRegistry.Chain> vis = visibleChains(p);
        int done = (int) vis.stream().filter(ch -> step(p, ch) >= ch.steps().size()).count();
        List<String> hl = new ArrayList<>(plugin.getConfig().getStringList("menu.categories.story.description"));
        if (!hl.isEmpty()) hl.add("");
        hl.add(gui("chains-count", "done", done, "total", vis.size()));
        hl.add(bar(done, vis.size()) + " &f" + percent(done, vis.size()) + "%");
        inv.setItem(HEADER, icon("story", item(catMat(Category.STORY, "icon", Material.WRITABLE_BOOK), catName(Category.STORY), hl, false, 1)));

        place(h, items, placers, pg);
        if (items.isEmpty()) inv.setItem(22, icon("empty", item(Material.BARRIER, gui("empty"), List.of(), false, 1)));
        nav(h, p, pg, pages, np -> openStory(p, np), () -> openMain(p));
        p.openInventory(inv);
    }

    // ── сюжет: шаги одной цепочки ──

    public void openChain(Player p, String chainId, int page) {
        QuestManager qm = plugin.quests();
        qm.refresh(p, false);
        QuestRegistry.Chain ch = plugin.registry().chains().get(chainId);
        if (ch == null) { openStory(p, 0); return; }
        boolean locked = ch.premium() && !qm.isPremium(p);
        int step = Math.min(step(p, ch), ch.steps().size()), total = ch.steps().size();

        List<ItemStack> items = new ArrayList<>();
        List<Runnable> placers = new ArrayList<>();
        List<Runnable> pins = new ArrayList<>();
        for (int i = 0; i < total; i++) {
            Quest q = ch.steps().get(i);
            int n = i + 1;
            pins.add(null);
            if (i < step) {
                List<String> lore = new ArrayList<>(q.description());
                lore.add("");
                lore.add(gui("step-passed"));
                items.add(icon("step-done", item(mat(plugin.getConfig().getString("gui.step-done-icon"), Material.LIME_STAINED_GLASS_PANE),
                        gui("step-done-name", "step", n, "quest", Text.strip(q.name())), lore, false, Math.min(64, n))));
                placers.add(() -> deny(p));
            } else if (i == step && !locked) {
                QuestManager.Entry e = entry(ch, i);
                items.add(questItem(p, e, gui("story-step", "step", n, "total", total)));
                pins.set(pins.size() - 1, () -> { click(p); qm.togglePin(p, e); openChain(p, chainId, page); });
                placers.add(() -> {
                    if (!qm.isDone(p, e)) { deny(p); qm.claim(p, e); return; }
                    qm.claim(p, e);
                    if (step(p, ch) >= ch.steps().size()) celebrate(p);
                    openChain(p, chainId, page);
                });
            } else {
                List<String> lore = locked
                        ? new ArrayList<>(plugin.getConfig().getStringList("premium.chain-locked-lore").stream().map(this::fill).toList())
                        : guiList("step-locked-lore", "prev", n - 1);
                items.add(icon("step-locked", item(mat(plugin.getConfig().getString("gui.step-locked-icon"), Material.GRAY_DYE),
                        gui("step-locked-name", "step", n), lore, false, Math.min(64, n))));
                placers.add(() -> deny(p));
            }
        }

        Holder h = new Holder();
        int pages = Math.max(1, (items.size() + INNER.length - 1) / INNER.length);
        int pg = Math.max(0, Math.min(page, pages - 1));
        Inventory inv = Bukkit.createInventory(h, 54, menuTitle("chain", title(ch.name(), pg, pages)));
        h.inv = inv;
        frame(inv, catMat(Category.STORY, "pane", Material.PURPLE_STAINED_GLASS_PANE),
                catMat(Category.STORY, "corner", Material.MAGENTA_STAINED_GLASS_PANE));

        List<String> hl = new ArrayList<>();
        if (ch.premium()) hl.add(premiumText("premium.chain-tag"));
        hl.addAll(ch.description());
        if (!ch.description().isEmpty()) hl.add("");
        hl.add(gui("story-progress", "done", step, "total", total));
        hl.add(bar(step, total) + " &f" + percent(step, total) + "%");
        if (step >= total) { hl.add(""); hl.add(gui("story-done")); }
        inv.setItem(HEADER, item(ch.icon(), ch.name(), hl, step >= total, 1));

        place(h, items, placers, pins, pg);
        nav(h, p, pg, pages, np -> openChain(p, chainId, np), () -> openStory(p, 0));
        p.openInventory(inv);
    }

    // ── карточка квеста ──

    private ItemStack questItem(Player p, QuestManager.Entry e, String stepLine) {
        QuestManager qm = plugin.quests();
        Quest q = e.quest();
        int prog = Math.min(qm.data(p).get(e.key()), q.amount());
        boolean claimed = qm.isClaimed(p, e), done = claimed || prog >= q.amount();
        if (claimed) prog = q.amount();

        List<String> lore = new ArrayList<>();
        if (stepLine != null) lore.add(stepLine);
        if (q.premium()) lore.add(premiumText("premium.quest-tag"));
        lore.addAll(q.description());
        lore.add("");
        lore.add(gui("status-progress", "progress", prog, "amount", q.amount(), "percent", percent(prog, q.amount())));
        lore.add(bar(prog, q.amount()));
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
        lore.add("");
        if (claimed) lore.add(gui("status-claimed"));
        else if (done) lore.add(gui("status-ready"));
        else lore.add(gui("status-left", "left", q.amount() - prog));
        boolean pinned = !claimed && qm.isPinned(p, e);
        if (!claimed) lore.add(gui(pinned ? "unpin-hint" : "pin-hint"));

        if (claimed) {
            ItemStack it = item(mat(plugin.getConfig().getString("gui.claimed-icon"), Material.LIME_STAINED_GLASS_PANE),
                    gui("claimed-name", "quest", Text.strip(q.name())), lore, false, 1);
            return questCards() ? questCard(it, q, "claimed") : icon("claimed", it);
        }
        String name = done ? gui("ready-name", "quest", q.name()) : q.name();
        if (pinned) name = gui("pinned-name", "quest", name);
        return questCard(item(q.icon(), name, lore, done, 1), q, done ? "ready" : "active");
    }

    // ── Ферма+ ──

    private Material lockedIcon() {
        return mat(plugin.getConfig().getString("premium.locked-icon"), Material.GOLD_BLOCK);
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
        List<String> lore = new ArrayList<>();
        for (String l : plugin.getConfig().getStringList(base + ".lore")) lore.add(fill(l));
        Long until = prem ? plugin.premium().expires(p.getUniqueId()) : null;
        if (until != null && until != PremiumStore.FOREVER) {
            lore.add("");
            lore.add(gui("premium-left", "time", fmt(Duration.ofMillis(until - System.currentTimeMillis()))));
        }
        Material m = mat(plugin.getConfig().getString(base + ".icon"), prem ? Material.GOLDEN_HOE : Material.WHEAT);
        return icon(prem ? "premium-active" : "premium-inactive", item(m, premiumText(base + ".name"), lore, prem, 1));
    }

    // ── клики ──

    @EventHandler
    public void onClick(InventoryClickEvent e) {
        if (!(e.getInventory().getHolder() instanceof Holder h)) return;
        e.setCancelled(true);
        if (!(e.getWhoClicked() instanceof Player)) return;
        if (e.getClickedInventory() == null || !(e.getClickedInventory().getHolder() instanceof Holder)) return;
        Runnable r = e.isRightClick() && h.rightActions.containsKey(e.getSlot()) ? h.rightActions.get(e.getSlot()) : h.actions.get(e.getSlot());
        if (r != null) r.run();
    }

    @EventHandler
    public void onDrag(InventoryDragEvent e) {
        if (e.getInventory().getHolder() instanceof Holder) e.setCancelled(true);
    }

    // ── помощники ──

    private List<QuestRegistry.Chain> visibleChains(Player p) {
        boolean prem = plugin.quests().isPremium(p);
        return plugin.registry().chains().values().stream().filter(ch -> !ch.premium() || prem).toList();
    }

    private int step(Player p, QuestRegistry.Chain ch) {
        return plugin.quests().data(p).storyStep.getOrDefault(ch.id(), 0);
    }

    private QuestManager.Entry entry(QuestRegistry.Chain ch, int step) {
        Quest q = ch.steps().get(step);
        return new QuestManager.Entry(q, "story:" + ch.id() + ":" + q.id(), ch.id());
    }

    private String title(String name, int page, int pages) {
        return pages > 1 ? gui("title-paged", "name", name, "page", page + 1, "pages", pages) : name;
    }

    /** Разложить предметы страницы по внутренним слотам. */
    private void place(Holder h, List<ItemStack> items, List<Runnable> actions, int page) { place(h, items, actions, null, page); }

    private void place(Holder h, List<ItemStack> items, List<Runnable> actions, List<Runnable> rightActions, int page) {
        int from = page * INNER.length;
        for (int i = 0; i < INNER.length && from + i < items.size(); i++) {
            h.inv.setItem(INNER[i], items.get(from + i));
            h.actions.put(INNER[i], actions.get(from + i));
            if (rightActions != null && rightActions.get(from + i) != null) h.rightActions.put(INNER[i], rightActions.get(from + i));
        }
    }

    /** Нижняя панель: назад, страницы. */
    private void nav(Holder h, Player p, int page, int pages, java.util.function.IntConsumer open, Runnable back) {
        h.inv.setItem(BACK, icon("back", item(Material.ARROW, gui("back"), List.of(), false, 1)));
        h.actions.put(BACK, () -> { click(p); back.run(); });
        if (page > 0) {
            h.inv.setItem(PREV, icon("prev", item(Material.SPECTRAL_ARROW, gui("prev-page", "page", page), List.of(), false, 1)));
            h.actions.put(PREV, () -> { turn(p); open.accept(page - 1); });
        }
        if (page + 1 < pages) {
            h.inv.setItem(NEXT, icon("next", item(Material.SPECTRAL_ARROW, gui("next-page", "page", page + 2), List.of(), false, 1)));
            h.actions.put(NEXT, () -> { turn(p); open.accept(page + 1); });
        }
    }

    // ── нарисованные фоны меню (ресурспак, шрифт zenquests:menu) ──

    /** Символы фонов в шрифте: сдвиг влево на 8, картинка 176x222, сдвиг обратно к началу названия. */
    private static final Map<String, Character> BACKGROUNDS = Map.of(
            "main", '\uE000', "daily", '\uE001', "weekly", '\uE002', "seasonal", '\uE003',
            "story", '\uE004', "chain", '\uE005');
    private static final char SHIFT_TO_EDGE = '\uE100', SHIFT_BACK = '\uE101';

    private boolean textured() { return plugin.getConfig().getBoolean("menu.textures.enabled", false); }

    /** Название окна: с включёнными текстурами перед текстом идёт фон-картинка из шрифта ресурспака. */
    private Component menuTitle(String background, String text) {
        Component title = Text.parse(text);
        Character bg = BACKGROUNDS.get(background);
        if (!textured() || bg == null) return title;
        Key font = Key.key(plugin.getConfig().getString("menu.textures.font", "zenquests:menu"));
        // menu.textures.sequence — порядок символов шрифта: сдвиги, HD-плитки сцены, {bg} — накладка меню, сдвиг назад
        String seq = plugin.getConfig().getString("menu.textures.sequence", "");
        if (seq == null || seq.isBlank()) seq = "" + SHIFT_TO_EDGE + "{bg}" + SHIFT_BACK;
        Component image = Component.text(seq.replace("{bg}", String.valueOf(bg))).font(font).color(NamedTextColor.WHITE);
        // название уже нарисовано на картинке (лента) — текст поверх арта не нужен; menu.textures.title: true вернёт его
        if (!plugin.getConfig().getBoolean("menu.textures.title", false)) return image;
        // соседние компоненты не наследуют шрифт друг друга — текст остаётся обычным
        return Component.empty().append(image).append(title);
    }

    /** Рамка: верх и низ — акцентный цвет, углы — свой, бока и середина — тёмные. С текстурами — пусто, рамку рисует фон. */
    private void frame(Inventory inv, Material accent, Material corner) {
        if (textured()) { inv.clear(); return; }
        ItemStack dark = item(mat(plugin.getConfig().getString("menu.background"), Material.BLACK_STAINED_GLASS_PANE), " ", List.of(), false, 1);
        ItemStack acc = item(accent, " ", List.of(), false, 1);
        ItemStack cor = item(corner, " ", List.of(), false, 1);
        int rows = inv.getSize() / 9;
        for (int i = 0; i < inv.getSize(); i++) {
            int row = i / 9, col = i % 9;
            boolean edgeRow = row == 0 || row == rows - 1, edgeCol = col == 0 || col == 8;
            if (edgeRow && edgeCol) inv.setItem(i, cor);
            else if (edgeRow || (edgeCol && (row == 1 || row == rows - 2))) inv.setItem(i, acc);
            else if (edgeCol) inv.setItem(i, dark);
            else inv.setItem(i, null);
        }
    }

    private ItemStack item(Material mat, String name, List<String> lore, boolean glow, int amount) {
        ItemStack it = new ItemStack(mat, Math.max(1, Math.min(mat.getMaxStackSize(), amount)));
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
            if (name.isBlank()) {
                // стекло рамки — без пустой подсказки при наведении
                try { m.setHideTooltip(true); } catch (Throwable ignored) { }
            } else if (tooltipStyle() != null) {
                try { m.setTooltipStyle(tooltipStyle()); } catch (Throwable ignored) { }
            }
            it.setItemMeta(m);
        }
        return it;
    }

    // ── карточки квестов: пергамент по состоянию + эмблема по типу задания (модели zenquests:quest_<state>_<emblem>) ──

    private boolean questCards() { return !plugin.getConfig().getString("menu.quest-cards", "").isBlank(); }

    /** Эмблема по типу задания — имя слоя в ресурспаке. */
    static String emblem(ObjectiveType t) {
        return switch (t) {
            case BREAK -> "pickaxe"; case PLACE -> "block"; case KILL -> "sword"; case FISH, CATCH_FISH, CATCH_RARITY -> "fish";
            case CRAFT -> "craft"; case SMELT -> "furnace"; case EAT -> "apple"; case ENCHANT -> "ench";
            case BREED -> "heart"; case TAME -> "bone"; case WALK -> "boots"; case PLAYTIME -> "clock";
            case CROP_HIT, CROP_HARVEST, CROP_BREAK -> "wheat"; case COOK, COOK_ITEM -> "pot"; case MILL -> "mill";
            case FLOUR_SACK -> "sack"; case EARN, SPEND -> "coin"; case FARM_VISIT -> "house"; case NPC_TALK, DIALOG -> "bubble";
        };
    }

    /** menu.quest-cards: шаблон модели, напр. "zenquests:quest_{state}_{emblem}"; пусто — обычный предмет квеста. */
    private ItemStack questCard(ItemStack it, Quest q, String state) {
        String tpl = plugin.getConfig().getString("menu.quest-cards", "");
        if (tpl == null || tpl.isBlank()) return it;
        NamespacedKey model = NamespacedKey.fromString(tpl.replace("{state}", state).replace("{emblem}", emblem(q.type())).toLowerCase());
        if (model == null) return it;
        ItemMeta m = it.getItemMeta();
        if (m != null) {
            try { m.setItemModel(model); it.setItemMeta(m); } catch (Throwable ignored) { }
        }
        return it;
    }

    /** Своя иконка из ресурспака (menu.icons.<key>, например zenquests:icon_daily) поверх обычного предмета. Пусто — как есть. */
    private ItemStack icon(String key, ItemStack it) {
        String s = plugin.getConfig().getString("menu.icons." + key, "");
        NamespacedKey model = s == null || s.isBlank() ? null : NamespacedKey.fromString(s.trim().toLowerCase());
        if (model == null) return it;
        ItemMeta m = it.getItemMeta();
        if (m != null) {
            try { m.setItemModel(model); it.setItemMeta(m); } catch (Throwable ignored) { }
        }
        return it;
    }

    /** Свой стиль подсказки (тултипа) из ресурспака — menu.tooltip-style, например zenquests:farm. Пусто — обычный. */
    private NamespacedKey tooltipStyle() {
        String s = plugin.getConfig().getString("menu.tooltip-style", "");
        return s == null || s.isBlank() ? null : NamespacedKey.fromString(s.trim().toLowerCase());
    }

    /** Полоска из 20 палочек: заполненные — зелёные. */
    private String bar(int v, int max) {
        int len = 20;
        int filled = max <= 0 ? 0 : (int) Math.round((double) len * Math.min(v, max) / max);
        String full = plugin.getConfig().getString("gui.bar-full", "&a"), empty = plugin.getConfig().getString("gui.bar-empty", "&8");
        String ch = plugin.getConfig().getString("gui.bar-char", "|");
        return full + ch.repeat(filled) + empty + ch.repeat(len - filled);
    }

    private int percent(int v, int max) { return max <= 0 ? 0 : (int) Math.floor(100.0 * Math.min(v, max) / max); }

    private void click(Player p) { sound(p, Sound.UI_BUTTON_CLICK, 0.5f, 1.2f); }
    private void turn(Player p) { sound(p, Sound.ITEM_BOOK_PAGE_TURN, 1f, 1f); }
    private void deny(Player p) { sound(p, Sound.BLOCK_NOTE_BLOCK_BASS, 0.7f, 0.6f); }
    private void celebrate(Player p) { sound(p, Sound.UI_TOAST_CHALLENGE_COMPLETE, 1f, 1f); }

    private void sound(Player p, Sound s, float vol, float pitch) {
        try { p.playSound(p.getLocation(), s, vol, pitch); } catch (Throwable ignored) { }
    }

    private String fmt(Duration d) { return Text.duration(d); }
}
