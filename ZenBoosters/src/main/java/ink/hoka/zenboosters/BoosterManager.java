package ink.hoka.zenboosters;

import org.bukkit.Bukkit;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

/** Активные бустеры (boosters.yml): глобальные и по игрокам; множитель = произведение или максимум (config stack). */
public final class BoosterManager implements Listener {

    /** Описание типа из config.yml. */
    public record Type(String id, String name, String icon, double max) {}
    /** Активный бустер. */
    public static final class Booster {
        public final String type; public final double mult; public final long expires; public final String by;
        Booster(String type, double mult, long expires, String by) { this.type = type; this.mult = mult; this.expires = expires; this.by = by; }
        public long left() { return Math.max(0, expires - System.currentTimeMillis()); }
        public boolean active() { return expires > System.currentTimeMillis(); }
    }

    private final ZenBoosters plugin;
    private final Map<String, Type> types = new LinkedHashMap<>();
    private final List<Booster> global = new ArrayList<>();
    private final Map<UUID, List<Booster>> personal = new LinkedHashMap<>();
    private final File file;
    private boolean dirty;

    public BoosterManager(ZenBoosters plugin) { this.plugin = plugin; file = new File(plugin.getDataFolder(), "boosters.yml"); }

    public Map<String, Type> types() { return Collections.unmodifiableMap(types); }
    public Type type(String id) { return id == null ? null : types.get(id.toLowerCase(Locale.ROOT)); }

    public void load() {
        types.clear();
        ConfigurationSection t = plugin.getConfig().getConfigurationSection("types");
        if (t != null) for (String id : t.getKeys(false)) {
            ConfigurationSection s = t.getConfigurationSection(id);
            types.put(id.toLowerCase(Locale.ROOT), new Type(id.toLowerCase(Locale.ROOT), s == null ? id : s.getString("name", id), s == null ? "" : s.getString("icon", ""), s == null ? 5 : s.getDouble("max", 5)));
        }
        global.clear(); personal.clear();
        if (!file.exists()) return;
        YamlConfiguration y = YamlConfiguration.loadConfiguration(file);
        for (Map<?, ?> m : y.getMapList("global")) { Booster b = read(m); if (b != null && b.active()) global.add(b); }
        ConfigurationSection ps = y.getConfigurationSection("players");
        if (ps != null) for (String k : ps.getKeys(false)) {
            try {
                UUID id = UUID.fromString(k); List<Booster> l = new ArrayList<>();
                for (Map<?, ?> m : ps.getMapList(k)) { Booster b = read(m); if (b != null && b.active()) l.add(b); }
                if (!l.isEmpty()) personal.put(id, l);
            } catch (IllegalArgumentException ignored) { }
        }
    }

    private static Booster read(Map<?, ?> m) {
        try { return new Booster(String.valueOf(m.get("type")), ((Number) m.get("mult")).doubleValue(), ((Number) m.get("expires")).longValue(), m.get("by") == null ? "?" : String.valueOf(m.get("by"))); }
        catch (Exception e) { return null; }
    }
    private static Map<String, Object> write(Booster b) { Map<String, Object> m = new LinkedHashMap<>(); m.put("type", b.type); m.put("mult", b.mult); m.put("expires", b.expires); m.put("by", b.by); return m; }

    public void save() {
        if (!dirty) return;
        YamlConfiguration y = new YamlConfiguration();
        List<Map<String, Object>> g = new ArrayList<>(); for (Booster b : global) if (b.active()) g.add(write(b)); y.set("global", g);
        for (Map.Entry<UUID, List<Booster>> e : personal.entrySet()) {
            List<Map<String, Object>> l = new ArrayList<>(); for (Booster b : e.getValue()) if (b.active()) l.add(write(b));
            if (!l.isEmpty()) y.set("players." + e.getKey(), l);
        }
        try { y.save(file); dirty = false; } catch (IOException e) { plugin.getLogger().warning("Не сохранился boosters.yml: " + e.getMessage()); }
    }

    // ── выдача ──

    public Booster addGlobal(String type, double mult, long millis, String by) {
        Booster b = new Booster(type, mult, System.currentTimeMillis() + millis, by);
        global.add(b); dirty = true; save();
        return b;
    }

    public Booster addPersonal(UUID id, String type, double mult, long millis, String by) {
        Booster b = new Booster(type, mult, System.currentTimeMillis() + millis, by);
        personal.computeIfAbsent(id, k -> new ArrayList<>()).add(b); dirty = true; save();
        return b;
    }

    /** Снять бустеры: type null — все. @return сколько снято */
    public int clear(UUID id, String type) {
        List<Booster> l = id == null ? global : personal.getOrDefault(id, new ArrayList<>());
        int before = l.size();
        l.removeIf(b -> type == null || b.type.equalsIgnoreCase(type));
        if (id != null && l.isEmpty()) personal.remove(id);
        if (before != l.size()) { dirty = true; save(); }
        return before - l.size();
    }

    public List<Booster> global() { return global.stream().filter(Booster::active).toList(); }
    public List<Booster> personal(UUID id) { return personal.getOrDefault(id, List.of()).stream().filter(Booster::active).toList(); }

    /** Итоговый множитель типа для игрока: личные × глобальные (stack: multiply) или максимум (stack: max), не выше types.<id>.max. */
    public double multiplier(UUID id, String type) {
        boolean multiply = !"max".equalsIgnoreCase(plugin.getConfig().getString("stack", "multiply"));
        double m = 1;
        for (Booster b : global) if (b.active() && b.type.equalsIgnoreCase(type)) m = multiply ? m * b.mult : Math.max(m, b.mult);
        if (id != null) for (Booster b : personal.getOrDefault(id, List.of())) if (b.active() && b.type.equalsIgnoreCase(type)) m = multiply ? m * b.mult : Math.max(m, b.mult);
        Type t = type(type);
        return t == null ? m : Math.min(t.max(), m);
    }

    /** Самый долгий активный бустер типа (личный или глобальный) — для плейсхолдеров «осталось». */
    public long left(UUID id, String type) {
        long best = 0;
        for (Booster b : global) if (b.active() && b.type.equalsIgnoreCase(type)) best = Math.max(best, b.left());
        if (id != null) for (Booster b : personal.getOrDefault(id, List.of())) if (b.active() && b.type.equalsIgnoreCase(type)) best = Math.max(best, b.left());
        return best;
    }

    /** Раз в секунду: истёкшие — убрать и сообщить. */
    public void tick() {
        List<Booster> gone = new ArrayList<>();
        global.removeIf(b -> { if (!b.active()) { gone.add(b); return true; } return false; });
        for (Booster b : gone) plugin.broadcast("expired-global", "type", name(b.type), "mult", fmt(b.mult));
        for (Map.Entry<UUID, List<Booster>> e : new ArrayList<>(personal.entrySet())) {
            List<Booster> pg = new ArrayList<>();
            e.getValue().removeIf(b -> { if (!b.active()) { pg.add(b); return true; } return false; });
            Player p = Bukkit.getPlayer(e.getKey());
            if (p != null) for (Booster b : pg) plugin.msg(p, "expired", "type", name(b.type), "mult", fmt(b.mult));
            if (e.getValue().isEmpty()) personal.remove(e.getKey());
        }
        if (!gone.isEmpty()) dirty = true;
        save();
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent e) {
        Player p = e.getPlayer();
        List<Booster> all = new ArrayList<>(global()); all.addAll(personal(p.getUniqueId()));
        if (all.isEmpty() || !plugin.getConfig().getBoolean("join-reminder", true)) return;
        Bukkit.getScheduler().runTaskLater(plugin, () -> { for (Booster b : all) if (b.active()) plugin.msg(p, "join-active", "type", name(b.type), "mult", fmt(b.mult), "left", time(b.left())); }, 40L);
    }

    public String name(String type) { Type t = type(type); return t == null ? type : t.name(); }
    public static String fmt(double m) { return (m == Math.rint(m) ? String.valueOf((long) m) : String.format(Locale.ROOT, "%.2f", m)).replace(".00", ""); }
    public static String time(long ms) {
        long s = ms / 1000, d = s / 86400, h = s % 86400 / 3600, m = s % 3600 / 60, sec = s % 60;
        if (d > 0) return d + "д " + h + "ч"; if (h > 0) return h + "ч " + m + "м"; if (m > 0) return m + "м " + sec + "с"; return sec + "с";
    }
    /** "30m", "2h", "1d", "90s", "1h30m" → миллисекунды; 0 — ошибка. */
    public static long parseTime(String s) {
        long total = 0; StringBuilder num = new StringBuilder();
        for (char c : s.toLowerCase(Locale.ROOT).toCharArray()) {
            if (Character.isDigit(c)) { num.append(c); continue; }
            if (num.length() == 0) return 0;
            long n = Long.parseLong(num.toString()); num.setLength(0);
            switch (c) { case 'd', 'д' -> total += n * 86400000L; case 'h', 'ч' -> total += n * 3600000L; case 'm', 'м' -> total += n * 60000L; case 's', 'с' -> total += n * 1000L; default -> { return 0; } }
        }
        if (num.length() > 0) total += Long.parseLong(num.toString()) * 60000L;   // голое число — минуты
        return total;
    }
}
