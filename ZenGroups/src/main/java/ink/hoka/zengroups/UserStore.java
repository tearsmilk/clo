package ink.hoka.zengroups;

import org.bukkit.configuration.file.YamlConfiguration;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Группы игроков: plugins/ZenGroups/users/<uuid>.yml — строки «группа=окончание_мс» (-1 — навсегда). */
public final class UserStore {

    public static final long FOREVER = -1L;

    /** Выданная группа и срок. */
    public static final class Entry {
        public final String group; public long until;
        Entry(String group, long until) { this.group = group; this.until = until; }
        public boolean active() { return until == FOREVER || until > System.currentTimeMillis(); }
    }

    private final ZenGroups plugin;
    private final Map<UUID, List<Entry>> cache = new HashMap<>();

    public UserStore(ZenGroups plugin) { this.plugin = plugin; }

    private File file(UUID id) { return new File(new File(plugin.getDataFolder(), "users"), id + ".yml"); }

    private List<Entry> raw(UUID id) {
        return cache.computeIfAbsent(id, k -> {
            List<Entry> l = new ArrayList<>();
            File f = file(k);
            if (!f.exists()) return l;
            for (String line : YamlConfiguration.loadConfiguration(f).getStringList("groups")) {
                int i = line.lastIndexOf('=');
                if (i <= 0) continue;
                try { l.add(new Entry(line.substring(0, i), Long.parseLong(line.substring(i + 1)))); } catch (NumberFormatException ignored) { }
            }
            return l;
        });
    }

    private void save(UUID id) {
        List<Entry> l = cache.get(id);
        if (l == null) return;
        YamlConfiguration y = new YamlConfiguration();
        List<String> lines = new ArrayList<>();
        for (Entry e : l) lines.add(e.group + "=" + e.until);
        y.set("groups", lines);
        try { file(id).getParentFile().mkdirs(); y.save(file(id)); }
        catch (IOException ex) { plugin.getLogger().warning("Не сохранился users/" + id + ".yml: " + ex.getMessage()); }
    }

    /** Активные записи; истёкшие удаляются (и возвращаются через expired, если передан список). */
    public List<Entry> entries(UUID id, List<Entry> expired) {
        List<Entry> l = raw(id);
        boolean changed = false;
        for (Iterator<Entry> it = l.iterator(); it.hasNext(); ) {
            Entry e = it.next();
            if (!e.active()) { it.remove(); changed = true; if (expired != null) expired.add(e); }
        }
        if (changed) save(id);
        return new ArrayList<>(l);
    }

    public Entry entry(UUID id, String group) {
        for (Entry e : entries(id, null)) if (e.group.equalsIgnoreCase(group)) return e;
        return null;
    }

    /** Добавить/продлить. Если уже есть навсегда — остаётся навсегда; иначе срок продлевается от текущего конца. */
    public Entry add(UUID id, String group, Long durationMs) {
        List<Entry> l = raw(id);
        Entry cur = null;
        for (Entry e : l) if (e.group.equalsIgnoreCase(group) && e.active()) cur = e;
        long until;
        if (durationMs == null) until = FOREVER;
        else if (cur != null && cur.until == FOREVER) until = FOREVER;
        else until = (cur != null ? cur.until : System.currentTimeMillis()) + durationMs;
        if (cur == null) { cur = new Entry(group, until); l.add(cur); } else cur.until = until;
        save(id);
        return cur;
    }

    /** Снять все группы и выдать одну. */
    public Entry set(UUID id, String group, Long durationMs) {
        raw(id).clear();
        return add(id, group, durationMs);
    }

    public boolean take(UUID id, String group) {
        boolean had = raw(id).removeIf(e -> e.group.equalsIgnoreCase(group));
        if (had) save(id);
        return had;
    }

    public void unload(UUID id) { cache.remove(id); }
}
