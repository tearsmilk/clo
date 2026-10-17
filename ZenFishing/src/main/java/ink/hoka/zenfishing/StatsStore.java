package ink.hoka.zenfishing;

import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.entity.Player;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Кэш статистики онлайн-игроков + чтение с диска для топа и /рыбалка stats. */
public final class StatsStore {

    private final ZenFishing plugin;
    private final Map<UUID, PlayerStats> cache = new HashMap<>();

    public StatsStore(ZenFishing plugin) { this.plugin = plugin; }

    private File file(UUID id) { return new File(new File(plugin.getDataFolder(), "players"), id + ".yml"); }

    public PlayerStats get(Player p) {
        PlayerStats s = cache.computeIfAbsent(p.getUniqueId(), id -> PlayerStats.load(file(id)));
        if (!p.getName().equals(s.name)) { s.name = p.getName(); s.dirty = true; }
        return s;
    }

    /** Для игрока не в сети — с диска (без кэша). */
    public PlayerStats peek(OfflinePlayer p) {
        PlayerStats c = cache.get(p.getUniqueId());
        return c != null ? c : PlayerStats.load(file(p.getUniqueId()));
    }

    public void save(UUID id) {
        PlayerStats s = cache.get(id);
        if (s == null) return;
        try { s.save(file(id)); }
        catch (IOException e) { plugin.getLogger().warning("Не сохранилась статистика " + id + ": " + e.getMessage()); }
    }

    public void saveDirty() { for (Map.Entry<UUID, PlayerStats> e : cache.entrySet()) if (e.getValue().dirty) save(e.getKey()); }

    public void unload(UUID id) { save(id); cache.remove(id); }

    /** Все известные рыбаки (кэш + файлы) — для топа. */
    public List<PlayerStats> everyone() {
        Map<UUID, PlayerStats> all = new HashMap<>();
        File dir = new File(plugin.getDataFolder(), "players");
        File[] files = dir.listFiles((d, n) -> n.endsWith(".yml"));
        if (files != null) for (File f : files) {
            try { UUID id = UUID.fromString(f.getName().substring(0, f.getName().length() - 4)); all.put(id, PlayerStats.load(f)); }
            catch (IllegalArgumentException ignored) { }
        }
        all.putAll(cache);
        for (Map.Entry<UUID, PlayerStats> e : all.entrySet()) if (e.getValue().name.isEmpty()) {
            String n = Bukkit.getOfflinePlayer(e.getKey()).getName();
            if (n != null) e.getValue().name = n;
        }
        return new ArrayList<>(all.values());
    }
}
