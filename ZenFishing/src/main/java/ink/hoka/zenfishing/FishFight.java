package ink.hoka.zenfishing;

import ink.hoka.zenfishing.util.Text;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.title.Title;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Sound;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerFishEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.player.PlayerToggleSneakEvent;
import org.bukkit.inventory.ItemStack;
import org.bukkit.scheduler.BukkitTask;

import java.time.Duration;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Вываживание: после поклёвки рыба не падает сама — в экшенбаре бежит маркер, нужно нажать Shift, когда он в зелёной зоне.
 * Нужное число попаданий, ширина зоны и скорость зависят от редкости (minigame.rarity.<id>); бонус «клёв» удочки и Ферма+
 * расширяют зону. Промах или пауза дольше timeout — рыба срывается. Успех — рыба выдаётся как обычный улов.
 */
public final class FishFight implements Listener {

    /** Текущая борьба игрока. */
    private final class Fight {
        final Player p; final Fish fish; final ItemStack rod; final Rods.Bonus bonus; final Location where; final boolean night; final double luck;
        final int need; int hits; final int len; int zoneStart, zoneLen; double pos; double speed; int dir = 1; int sinceHit; int misses;
        BukkitTask task;
        Fight(Player p, Fish fish, ItemStack rod, Rods.Bonus bonus, Location where, boolean night, double luck, int need, int len) {
            this.p = p; this.fish = fish; this.rod = rod; this.bonus = bonus; this.where = where; this.night = night; this.luck = luck; this.need = need; this.len = len;
        }
    }

    private final ZenFishing plugin;
    private final FishingListener catcher;
    private final Map<UUID, Fight> fights = new HashMap<>();

    public FishFight(ZenFishing plugin, FishingListener catcher) { this.plugin = plugin; this.catcher = catcher; }

    private ConfigurationSection cfg() {
        ConfigurationSection c = plugin.getConfig().getConfigurationSection("minigame");
        return c != null ? c : plugin.getConfig().createSection("minigame");
    }
    public boolean enabled() { return cfg().getBoolean("enabled", true); }
    public boolean active(Player p) { return fights.containsKey(p.getUniqueId()); }

    private double rar(Fish f, String key, double def) {
        ConfigurationSection r = cfg().getConfigurationSection("rarity." + f.rarity().id().toLowerCase(Locale.ROOT));
        return r != null ? r.getDouble(key, def) : def;
    }

    /** Начать борьбу (вызывается из FishingListener вместо выдачи рыбы). */
    public void start(Player p, Fish f, ItemStack rod, Rods.Bonus b, Location where, boolean night, double luck) {
        cancel(p);
        int len = Math.max(10, cfg().getInt("bar-length", 24));
        Fight g = new Fight(p, f, rod, b, where, night, luck, (int) Math.max(1, rar(f, "hits", 1)), len);
        double zone = rar(f, "zone", 8) + b.bite() * cfg().getDouble("zone-per-bite", 6) + (plugin.isPremium(p) ? cfg().getDouble("zone-premium", 1) : 0);
        g.zoneLen = (int) Math.max(2, Math.min(len - 2, Math.round(zone)));
        g.speed = Math.max(0.2, rar(f, "speed", 0.8));
        newZone(g);
        g.pos = 0; g.dir = 1;
        fights.put(p.getUniqueId(), g);
        p.playSound(p.getLocation(), Sound.ENTITY_FISHING_BOBBER_SPLASH, 1f, 0.8f);
        if (cfg().getBoolean("title", true)) {
            p.showTitle(Title.title(Text.parse(plugin.getConfig().getString("messages.fight-title", "&bКлюёт!")),
                    Text.parse(plugin.getConfig().getString("messages.fight-subtitle", "&7Жми &fShift&7, когда маркер в зелёной зоне")),
                    Title.Times.times(Duration.ofMillis(100), Duration.ofMillis(900), Duration.ofMillis(300))));
        }
        g.task = Bukkit.getScheduler().runTaskTimer(plugin, () -> tick(g), 1L, 1L);
    }

    private void newZone(Fight g) {
        g.zoneStart = ThreadLocalRandom.current().nextInt(1, Math.max(2, g.len - g.zoneLen - 1));
        g.sinceHit = 0;
    }

    private void tick(Fight g) {
        if (!g.p.isOnline() || !fights.containsKey(g.p.getUniqueId())) { stop(g); return; }
        g.pos += g.speed * g.dir;
        if (g.pos >= g.len - 1) { g.pos = g.len - 1; g.dir = -1; }
        if (g.pos <= 0) { g.pos = 0; g.dir = 1; }
        if (++g.sinceHit > cfg().getInt("timeout-ticks", 70)) { escape(g, "fight-timeout"); return; }
        if (!plugin.rods().isRod(g.p.getInventory().getItemInMainHand()) && !plugin.rods().isRod(g.p.getInventory().getItemInOffHand())) { escape(g, "fight-escape"); return; }
        g.p.sendActionBar(bar(g));
    }

    private boolean inZone(Fight g) { int m = (int) Math.round(g.pos); return m >= g.zoneStart && m < g.zoneStart + g.zoneLen; }

    private Component bar(Fight g) {
        int m = (int) Math.round(g.pos);
        StringBuilder sb = new StringBuilder();
        String wave = cfg().getString("bar.wave", "&3≈"), zone = cfg().getString("bar.zone", "&a▮"), mark = cfg().getString("bar.marker", "&f◆"), markIn = cfg().getString("bar.marker-in", "&e◆");
        for (int i = 0; i < g.len; i++) {
            boolean z = i >= g.zoneStart && i < g.zoneStart + g.zoneLen;
            if (i == m) sb.append(z ? markIn : mark); else sb.append(z ? zone : wave);
        }
        StringBuilder dots = new StringBuilder();
        for (int i = 0; i < g.need; i++) dots.append(i < g.hits ? cfg().getString("bar.hit", "&a●") : cfg().getString("bar.todo", "&8●"));
        String s = cfg().getString("bar.format", "&b🎣 &8[{bar}&8] {dots}").replace("{bar}", sb).replace("{dots}", dots);
        return Text.parse(s);
    }

    @EventHandler(ignoreCancelled = true)
    public void onSneak(PlayerToggleSneakEvent e) {
        if (!e.isSneaking()) return;
        Fight g = fights.get(e.getPlayer().getUniqueId());
        if (g == null) return;
        if (inZone(g)) {
            g.hits++;
            g.p.playSound(g.p.getLocation(), Sound.BLOCK_NOTE_BLOCK_PLING, 0.8f, 1.0f + 0.15f * g.hits);
            if (g.hits >= g.need) { success(g); return; }
            // следующая фаза: новая зона, чуть быстрее
            g.speed *= cfg().getDouble("speed-up", 1.12);
            newZone(g);
            g.p.sendActionBar(bar(g));
        } else {
            g.misses++;
            g.p.playSound(g.p.getLocation(), Sound.ENTITY_ITEM_BREAK, 0.6f, 0.7f);
            if (g.misses > cfg().getInt("misses-allowed", 0)) escape(g, "fight-escape");
            else plugin.msg(g.p, "fight-miss");
        }
    }

    /** Пока идёт борьба — новый заброс запрещён (иначе рыба уйдёт, а удочка улетит). */
    @EventHandler(priority = EventPriority.LOWEST)
    public void onCast(PlayerFishEvent e) {
        if (e.getState() == PlayerFishEvent.State.FISHING && active(e.getPlayer())) e.setCancelled(true);
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) { Fight g = fights.remove(e.getPlayer().getUniqueId()); if (g != null) stop(g); }

    private void success(Fight g) {
        stop(g); fights.remove(g.p.getUniqueId());
        g.p.sendActionBar(Text.parse(plugin.getConfig().getString("messages.fight-success", "&a✔ Поймал!")));
        catcher.deliver(g.p, g.fish, g.rod, g.bonus, g.where, g.night, g.luck);
    }

    private void escape(Fight g, String msgKey) {
        stop(g); fights.remove(g.p.getUniqueId());
        g.p.sendActionBar(Text.parse(plugin.getConfig().getString("messages." + msgKey, "&cСорвалась!")));
        g.p.playSound(g.p.getLocation(), Sound.ENTITY_PLAYER_SPLASH, 0.8f, 0.6f);
        int xp = cfg().getInt("escape-xp", 0);
        if (xp > 0 && plugin.rods().isRod(g.rod)) plugin.rods().addXp(g.p, g.rod, xp);
    }

    private void stop(Fight g) { if (g.task != null) g.task.cancel(); }

    public void cancel(Player p) { Fight g = fights.remove(p.getUniqueId()); if (g != null) stop(g); }
    public void cancelAll() { for (Fight g : fights.values()) stop(g); fights.clear(); }
}
