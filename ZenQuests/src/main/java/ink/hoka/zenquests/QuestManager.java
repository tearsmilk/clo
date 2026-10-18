package ink.hoka.zenquests;

import ink.hoka.zenquests.model.Category;
import ink.hoka.zenquests.model.ObjectiveType;
import ink.hoka.zenquests.model.Quest;
import ink.hoka.zenquests.util.Text;
import net.kyori.adventure.bossbar.BossBar;
import org.bukkit.Bukkit;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.scheduler.BukkitTask;

import java.io.File;
import java.time.DayOfWeek;
import java.time.Duration;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.temporal.IsoFields;
import java.time.temporal.TemporalAdjusters;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Выдача квестов по периодам, прогресс, награды. */
public final class QuestManager {

    /** Активный квест игрока: сам квест и ключ его прогресса. chain — для сюжетных. */
    public record Entry(Quest quest, String key, String chain) {}

    private final ZenQuests plugin;
    private final Map<UUID, PlayerData> online = new HashMap<>();
    private final Map<UUID, BossBar> bars = new HashMap<>();
    private final Map<UUID, BukkitTask> barTasks = new HashMap<>();

    public QuestManager(ZenQuests plugin) { this.plugin = plugin; }

    // ── время ──

    public ZoneId zone() {
        try { return ZoneId.of(plugin.getConfig().getString("timezone", "Europe/Moscow")); }
        catch (Exception e) { return ZoneId.systemDefault(); }
    }

    public ZonedDateTime now() { return ZonedDateTime.now(zone()); }

    public LocalDate today() { return now().toLocalDate(); }

    private String weekKey(LocalDate d) {
        return d.get(IsoFields.WEEK_BASED_YEAR) + "-W" + d.get(IsoFields.WEEK_OF_WEEK_BASED_YEAR);
    }

    public Duration untilDailyReset() {
        ZonedDateTime n = now();
        return Duration.between(n, n.toLocalDate().plusDays(1).atStartOfDay(zone()));
    }

    public Duration untilWeeklyReset() {
        ZonedDateTime n = now();
        LocalDate monday = n.toLocalDate().with(TemporalAdjusters.next(DayOfWeek.MONDAY));
        return Duration.between(n, monday.atStartOfDay(zone()));
    }

    public Duration untilSeasonEnd(QuestRegistry.Season s) {
        ZonedDateTime n = now();
        return Duration.between(n, s.end().plusDays(1).atStartOfDay(zone()));
    }

    // ── подписка Ферма+ ──

    public boolean isPremium(Player p) {
        return p.hasPermission(plugin.getConfig().getString("premium.permission", "zenquests.premium"))
                || plugin.premium().active(p.getUniqueId());
    }

    /** Видит ли игрок квест: премиум-квесты — только с подпиской. */
    public boolean canSee(Player p, Quest q) { return !q.premium() || isPremium(p); }

    // ── данные игроков ──

    private File file(UUID id) { return new File(plugin.getDataFolder(), "players/" + id + ".yml"); }

    public PlayerData data(Player p) {
        return online.computeIfAbsent(p.getUniqueId(), id -> PlayerData.load(file(id)));
    }

    public void save(Player p) {
        PlayerData d = online.get(p.getUniqueId());
        if (d == null) return;
        try { d.save(file(p.getUniqueId())); }
        catch (Exception e) { plugin.getLogger().warning("Не сохранились квесты " + p.getName() + ": " + e.getMessage()); }
    }

    public void unload(Player p) {
        save(p);
        online.remove(p.getUniqueId());
        hideBar(p);
    }

    public void saveDirty() {
        for (Player p : Bukkit.getOnlinePlayers()) {
            PlayerData d = online.get(p.getUniqueId());
            if (d != null && d.dirty) save(p);
        }
    }

    /** Сбросить прогресс игрока. what: daily|weekly|seasonal|story|all */
    public void reset(Player p, String what) {
        PlayerData d = data(p);
        boolean all = what.equals("all");
        if (all || what.equals("daily")) { d.dailyPeriod = ""; d.daily.clear(); d.dailyPremium.clear(); d.clearPrefix("daily:"); }
        if (all || what.equals("weekly")) { d.weeklyPeriod = ""; d.weekly.clear(); d.weeklyPremium.clear(); d.clearPrefix("weekly:"); }
        if (all || what.equals("seasonal")) d.clearPrefix("seasonal:");
        if (all || what.equals("story")) { d.storyStep.clear(); d.clearPrefix("story:"); }
        refresh(p, false);
        save(p);
    }

    /** Выдать новые ежедневные/еженедельные, если сменился день/неделя; убрать старые сезоны. */
    public void refresh(Player p, boolean notify) {
        PlayerData d = data(p);
        QuestRegistry reg = plugin.registry();
        LocalDate today = today();

        String day = today.toString();
        if (!day.equals(d.dailyPeriod)) {
            boolean hadBefore = !d.dailyPeriod.isEmpty();
            d.clearPrefix("daily:");
            d.daily = pickRandom(reg.dailyPool(), reg.dailyCount());
            // премиум-набор выдаётся всем сразу: купил Ферма+ посреди дня — квесты уже на месте
            d.dailyPremium = pickRandom(reg.dailyPremiumPool(), reg.dailyPremiumCount());
            d.dailyPeriod = day;
            d.dirty = true;
            if (notify && hadBefore && !d.daily.isEmpty()) plugin.msg(p, "new-day");
            autoPinDaily(p);
        } else if (!d.pinnedInit) {
            autoPinDaily(p);   // первый вход после обновления: закрепить уже выданные ежедневные
        }
        String week = weekKey(today);
        if (d.weeklyPremium.isEmpty() && !reg.weeklyPremiumPool().isEmpty() && week.equals(d.weeklyPeriod)) {
            d.weeklyPremium = pickRandom(reg.weeklyPremiumPool(), reg.weeklyPremiumCount());
            d.dirty = true;
        }
        // в старых сохранениях премиум-набора нет — добираем, не трогая обычные
        if (d.dailyPremium.isEmpty() && !reg.dailyPremiumPool().isEmpty() && day.equals(d.dailyPeriod)) {
            d.dailyPremium = pickRandom(reg.dailyPremiumPool(), reg.dailyPremiumCount());
            d.dirty = true;
        }
        if (!week.equals(d.weeklyPeriod)) {
            d.clearPrefix("weekly:");
            d.weekly = pickRandom(reg.weeklyPool(), reg.weeklyCount());
            d.weeklyPremium = pickRandom(reg.weeklyPremiumPool(), reg.weeklyPremiumCount());
            d.weeklyPeriod = week;
            d.dirty = true;
        }
        QuestRegistry.Season season = reg.activeSeason(today);
        String keep = season == null ? null : "seasonal:" + season.id() + ":";
        boolean stale = d.progress.keySet().stream().anyMatch(k -> k.startsWith("seasonal:") && (keep == null || !k.startsWith(keep)))
                || d.claimed.stream().anyMatch(k -> k.startsWith("seasonal:") && (keep == null || !k.startsWith(keep)));
        if (stale) {
            d.progress.keySet().removeIf(k -> k.startsWith("seasonal:") && (keep == null || !k.startsWith(keep)));
            d.claimed.removeIf(k -> k.startsWith("seasonal:") && (keep == null || !k.startsWith(keep)));
            d.dirty = true;
        }
    }

    private List<String> pickRandom(List<Quest> pool, int count) {
        List<Quest> copy = new ArrayList<>(pool);
        Collections.shuffle(copy);
        List<String> out = new ArrayList<>();
        for (int i = 0; i < Math.min(count, copy.size()); i++) out.add(copy.get(i).id());
        return out;
    }

    // ── активные квесты ──

    public List<Entry> entries(Player p, Category cat) {
        PlayerData d = data(p);
        QuestRegistry reg = plugin.registry();
        List<Entry> out = new ArrayList<>();
        switch (cat) {
            case DAILY -> {
                for (String id : d.daily) {
                    Quest q = reg.find(Category.DAILY, id);
                    if (q != null) out.add(new Entry(q, "daily:" + id, null));
                }
                if (isPremium(p)) for (String id : d.dailyPremium) {
                    Quest q = reg.find(Category.DAILY, id);
                    if (q != null) out.add(new Entry(q, "daily:" + id, null));
                }
            }
            case WEEKLY -> {
                for (String id : d.weekly) {
                    Quest q = reg.find(Category.WEEKLY, id);
                    if (q != null) out.add(new Entry(q, "weekly:" + id, null));
                }
                if (isPremium(p)) for (String id : d.weeklyPremium) {
                    Quest q = reg.find(Category.WEEKLY, id);
                    if (q != null) out.add(new Entry(q, "weekly:" + id, null));
                }
            }
            case SEASONAL -> {
                QuestRegistry.Season s = reg.activeSeason(today());
                if (s != null) for (Quest q : s.quests())
                    if (canSee(p, q)) out.add(new Entry(q, "seasonal:" + s.id() + ":" + q.id(), null));
            }
            case STORY -> {
                for (QuestRegistry.Chain c : reg.chains().values()) {
                    if (c.premium() && !isPremium(p)) continue;
                    int step = d.storyStep.getOrDefault(c.id(), 0);
                    if (step < c.steps().size()) {
                        Quest q = c.steps().get(step);
                        out.add(new Entry(q, "story:" + c.id() + ":" + q.id(), c.id()));
                    }
                }
            }
        }
        return out;
    }

    public boolean isDone(Player p, Entry e) { return data(p).get(e.key()) >= e.quest().amount(); }

    public boolean isClaimed(Player p, Entry e) { return data(p).claimed.contains(e.key()); }

    // ── прогресс ──

    public void progress(Player p, ObjectiveType type, String target, int amount) {
        if (amount <= 0) return;
        refresh(p, true);
        PlayerData d = data(p);
        for (Category cat : Category.values()) {
            for (Entry e : entries(p, cat)) {
                Quest q = e.quest();
                if (!q.matches(type, target)) continue;
                if (d.claimed.contains(e.key())) continue;
                int cur = d.get(e.key());
                if (cur >= q.amount()) continue;
                int next = Math.min(q.amount(), cur + amount);
                d.progress.put(e.key(), next);
                d.dirty = true;
                showBar(p, q, next);
                if (next >= q.amount()) onComplete(p, e);
            }
        }
    }

    private void onComplete(Player p, Entry e) {
        try { p.playSound(p.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 0.8f, 1.2f); } catch (Throwable ignored) { }
        if (plugin.getConfig().getBoolean("auto-claim", false)) {
            give(p, e);
            plugin.msg(p, "completed-auto", "quest", e.quest().name());
        } else {
            plugin.msg(p, "completed", "quest", e.quest().name());
        }
        save(p);
    }

    // ── закрепление в худе (BetterHud) ──

    public int maxPinned() { return Math.max(1, plugin.getConfig().getInt("hud.max-pinned", 4)); }

    public boolean isPinned(Player p, Entry e) { return data(p).pinned.contains(e.key()); }

    /** Все квесты игрока по всем категориям (для поиска закреплённых по ключу). */
    private List<Entry> allEntries(Player p) {
        List<Entry> out = new ArrayList<>();
        for (Category c : Category.values()) out.addAll(entries(p, c));
        return out;
    }

    /** Закреплённые квесты по порядку; устаревшие и уже выполненные/полученные ключи вычищаются. */
    public List<Entry> pinnedEntries(Player p) {
        PlayerData d = data(p);
        if (d.pinned.isEmpty()) return List.of();
        Map<String, Entry> byKey = new HashMap<>();
        for (Entry e : allEntries(p)) byKey.put(e.key(), e);
        List<Entry> out = new ArrayList<>();
        boolean changed = false;
        for (Iterator<String> it = d.pinned.iterator(); it.hasNext(); ) {
            String k = it.next();
            Entry e = byKey.get(k);
            if (e == null || isClaimed(p, e)) { it.remove(); changed = true; continue; }
            out.add(e);
        }
        if (changed) d.dirty = true;
        return out;
    }

    /** Закрепить/открепить. @return новое состояние; сообщение игроку уже отправлено. */
    public boolean togglePin(Player p, Entry e) {
        PlayerData d = data(p);
        if (d.pinned.remove(e.key())) { d.dirty = true; plugin.msg(p, "unpinned", "quest", e.quest().name()); return false; }
        if (pinnedEntries(p).size() >= maxPinned()) { plugin.msg(p, "pin-full", "max", maxPinned()); return true; }
        d.pinned.add(e.key()); d.dirty = true;
        plugin.msg(p, "pinned", "quest", e.quest().name());
        return true;
    }

    /** Новые ежедневные закрепляются сами (hud.auto-pin-daily), пока есть место. */
    private void autoPinDaily(Player p) {
        PlayerData d = data(p);
        d.pinnedInit = true; d.dirty = true;
        if (!plugin.getConfig().getBoolean("hud.auto-pin-daily", true)) return;
        for (Entry e : entries(p, Category.DAILY)) {
            if (d.pinned.size() >= maxPinned()) break;
            if (!d.pinned.contains(e.key())) { d.pinned.add(e.key()); d.dirty = true; }
        }
    }

    /** Забрать награду (из меню). @return сообщение уже отправлено игроку. */
    public void claim(Player p, Entry e) {
        PlayerData d = data(p);
        if (d.claimed.contains(e.key())) { plugin.msg(p, "already-claimed"); return; }
        if (d.get(e.key()) < e.quest().amount()) {
            plugin.msg(p, "not-done", "progress", d.get(e.key()), "amount", e.quest().amount());
            return;
        }
        give(p, e);
        plugin.msg(p, "claimed", "quest", e.quest().name());
        try { p.playSound(p.getLocation(), Sound.ENTITY_PLAYER_LEVELUP, 1f, 1.3f); } catch (Throwable ignored) { }
        save(p);
    }

    private void give(Player p, Entry e) {
        PlayerData d = data(p);
        run(p, e.quest().rewardCommands());
        // бонус Ферма+ — сверху обычной награды
        if (isPremium(p) && !e.quest().premiumCommands().isEmpty()) {
            run(p, e.quest().premiumCommands());
            plugin.msg(p, "premium-bonus", "quest", e.quest().name());
        }
        if (e.chain() != null) {
            // сюжет: переходим к следующему шагу, прогресс шага больше не нужен
            d.storyStep.merge(e.chain(), 1, Integer::sum);
            d.progress.remove(e.key());
        } else {
            d.claimed.add(e.key());
        }
        d.dirty = true;
    }

    private void run(Player p, List<String> cmds) {
        for (String cmd : cmds) {
            String c = cmd.replace("{player}", p.getName());
            if (c.startsWith("/")) c = c.substring(1);
            try { Bukkit.dispatchCommand(Bukkit.getConsoleSender(), c); }
            catch (Exception ex) { plugin.getLogger().warning("Награда '" + c + "' не выполнилась: " + ex.getMessage()); }
        }
    }

    // ── полоска прогресса ──

    private void showBar(Player p, Quest q, int value) {
        if (!plugin.getConfig().getBoolean("bossbar.enabled", true)) return;
        float f = Math.max(0f, Math.min(1f, value / (float) q.amount()));
        var title = Text.parse(q.name() + " &7" + value + "/" + q.amount());
        BossBar bar = bars.get(p.getUniqueId());
        if (bar == null) {
            bar = BossBar.bossBar(title, f, BossBar.Color.GREEN, BossBar.Overlay.PROGRESS);
            bars.put(p.getUniqueId(), bar);
            p.showBossBar(bar);
        } else {
            bar.name(title);
            bar.progress(f);
            p.showBossBar(bar);
        }
        BukkitTask old = barTasks.remove(p.getUniqueId());
        if (old != null) old.cancel();
        long ticks = 20L * Math.max(1, plugin.getConfig().getInt("bossbar.seconds", 3));
        barTasks.put(p.getUniqueId(), Bukkit.getScheduler().runTaskLater(plugin, () -> hideBar(p), ticks));
    }

    private void hideBar(Player p) {
        BossBar bar = bars.remove(p.getUniqueId());
        if (bar != null) p.hideBossBar(bar);
        BukkitTask t = barTasks.remove(p.getUniqueId());
        if (t != null) t.cancel();
    }
}
