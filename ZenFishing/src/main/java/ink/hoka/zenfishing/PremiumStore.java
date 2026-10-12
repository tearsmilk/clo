package ink.hoka.zenfishing;

import org.bukkit.configuration.file.YamlConfiguration;

import java.io.File;
import java.io.IOException;
import java.time.Duration;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

/**
 * Подписка, выданная вручную командой /рыбалка premium. Работает вместе с правом из config.yml:
 * подписчик — тот, у кого есть право ИЛИ активная выдача здесь.
 * Хранится в plugins/ZenFishing/premium.yml: uuid → время окончания (мс), -1 — навсегда.
 */
public final class PremiumStore {

    public static final long FOREVER = -1L;

    private final ZenFishing plugin;
    private final Map<UUID, Long> until = new HashMap<>();

    public PremiumStore(ZenFishing plugin) { this.plugin = plugin; }

    private File file() { return new File(plugin.getDataFolder(), "premium.yml"); }

    public void load() {
        until.clear();
        YamlConfiguration y = YamlConfiguration.loadConfiguration(file());
        for (String k : y.getKeys(false)) {
            try { until.put(UUID.fromString(k), y.getLong(k)); }
            catch (IllegalArgumentException ignored) { }
        }
    }

    private void save() {
        YamlConfiguration y = new YamlConfiguration();
        for (Map.Entry<UUID, Long> e : until.entrySet()) y.set(e.getKey().toString(), e.getValue());
        try { y.save(file()); }
        catch (IOException e) { plugin.getLogger().warning("Не сохранился premium.yml: " + e.getMessage()); }
    }

    /** Активна ли выданная вручную подписка. Истёкшие записи удаляются. */
    public boolean active(UUID id) {
        Long t = until.get(id);
        if (t == null) return false;
        if (t == FOREVER || t > System.currentTimeMillis()) return true;
        until.remove(id);
        save();
        return false;
    }

    /** Время окончания (мс) или FOREVER; null — подписки нет. */
    public Long expires(UUID id) { return active(id) ? until.get(id) : null; }

    /**
     * Выдать подписку. duration == null — навсегда.
     * Если подписка уже идёт — срок продлевается от её окончания.
     * @return новое время окончания или FOREVER
     */
    public long give(UUID id, Duration duration) {
        long next;
        if (duration == null) next = FOREVER;
        else {
            Long cur = expires(id);
            if (cur != null && cur == FOREVER) return FOREVER;
            long from = cur != null ? cur : System.currentTimeMillis();
            next = from + duration.toMillis();
        }
        until.put(id, next);
        save();
        return next;
    }

    /** @return была ли подписка */
    public boolean take(UUID id) {
        boolean had = active(id);
        until.remove(id);
        save();
        return had;
    }

    /** Срок: 30d, 12h, 45m, 2w (можно 1d12h). forever / навсегда / пусто — null (навсегда). */
    public static Duration parse(String s) {
        if (s == null) return null;
        String in = s.trim().toLowerCase(Locale.ROOT);
        if (in.isEmpty() || in.equals("forever") || in.equals("навсегда") || in.equals("perm")) return null;
        Duration total = Duration.ZERO;
        StringBuilder num = new StringBuilder();
        for (char c : in.toCharArray()) {
            if (Character.isDigit(c)) { num.append(c); continue; }
            if (num.isEmpty()) throw new IllegalArgumentException(s);
            long n = Long.parseLong(num.toString());
            num.setLength(0);
            total = total.plus(switch (c) {
                case 'w', 'н' -> Duration.ofDays(7 * n);
                case 'd', 'д' -> Duration.ofDays(n);
                case 'h', 'ч' -> Duration.ofHours(n);
                case 'm', 'м' -> Duration.ofMinutes(n);
                default -> throw new IllegalArgumentException(s);
            });
        }
        if (!num.isEmpty()) total = total.plusDays(Long.parseLong(num.toString()));   // просто число — дни
        if (total.isZero() || total.isNegative()) throw new IllegalArgumentException(s);
        return total;
    }
}
