package ink.hoka.zenquests;

import ink.hoka.zenquests.model.Category;
import ink.hoka.zenquests.model.ObjectiveType;
import ink.hoka.zenquests.model.Quest;
import org.bukkit.Material;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.plugin.Plugin;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Все квесты из quests.yml: пулы ежедневных/еженедельных, сезоны, сюжетные цепочки. */
public final class QuestRegistry {

    public record Season(String id, String name, LocalDate start, LocalDate end, List<Quest> quests) {
        public boolean active(LocalDate today) { return !today.isBefore(start) && !today.isAfter(end); }
    }

    public record Chain(String id, String name, Material icon, List<String> description, List<Quest> steps, boolean premium) {}

    private final Plugin plugin;
    private int dailyCount = 3, weeklyCount = 3, dailyPremiumCount = 2, weeklyPremiumCount = 2;
    private final List<Quest> dailyPool = new ArrayList<>();
    private final List<Quest> weeklyPool = new ArrayList<>();
    private final List<Quest> dailyPremiumPool = new ArrayList<>();
    private final List<Quest> weeklyPremiumPool = new ArrayList<>();
    private final List<Season> seasons = new ArrayList<>();
    private final Map<String, Chain> chains = new LinkedHashMap<>();
    private final Map<String, Quest> byKey = new LinkedHashMap<>();   // "daily:id" → квест

    public QuestRegistry(Plugin plugin) { this.plugin = plugin; }

    public void load(FileConfiguration c) {
        dailyPool.clear(); weeklyPool.clear(); dailyPremiumPool.clear(); weeklyPremiumPool.clear();
        seasons.clear(); chains.clear(); byKey.clear();

        dailyCount = c.getInt("daily.count", 3);
        dailyPremiumCount = c.getInt("daily.premium-count", 2);
        readPool(c.getConfigurationSection("daily.quests"), Category.DAILY, dailyPool, false);
        readPool(c.getConfigurationSection("daily.premium-quests"), Category.DAILY, dailyPremiumPool, true);
        weeklyCount = c.getInt("weekly.count", 3);
        weeklyPremiumCount = c.getInt("weekly.premium-count", 2);
        readPool(c.getConfigurationSection("weekly.quests"), Category.WEEKLY, weeklyPool, false);
        readPool(c.getConfigurationSection("weekly.premium-quests"), Category.WEEKLY, weeklyPremiumPool, true);

        ConfigurationSection ss = c.getConfigurationSection("seasons");
        if (ss != null) for (String sid : ss.getKeys(false)) {
            ConfigurationSection s = ss.getConfigurationSection(sid);
            if (s == null) continue;
            LocalDate start = date(s.get("start"), sid), end = date(s.get("end"), sid);
            if (start == null || end == null) continue;
            List<Quest> qs = new ArrayList<>();
            readPool(s.getConfigurationSection("quests"), Category.SEASONAL, qs, false);
            seasons.add(new Season(sid, s.getString("name", sid), start, end, qs));
        }

        ConfigurationSection cs = c.getConfigurationSection("story");
        if (cs != null) for (String cid : cs.getKeys(false)) {
            ConfigurationSection s = cs.getConfigurationSection(cid);
            if (s == null) continue;
            List<Quest> steps = new ArrayList<>();
            readPool(s.getConfigurationSection("steps"), Category.STORY, steps, s.getBoolean("premium", false));
            if (steps.isEmpty()) continue;
            chains.put(cid, new Chain(cid, s.getString("name", cid), material(s.getString("icon"), Material.WRITABLE_BOOK),
                    s.getStringList("description"), steps,
                    s.getBoolean("premium", false)));
        }

        int seasonal = seasons.stream().mapToInt(x -> x.quests().size()).sum();
        int story = chains.values().stream().mapToInt(x -> x.steps().size()).sum();
        plugin.getLogger().info("Квесты: ежедневных " + dailyPool.size() + " (+" + dailyPremiumPool.size() + " Ферма+)"
                + ", еженедельных " + weeklyPool.size() + " (+" + weeklyPremiumPool.size() + " Ферма+)"
                + ", сезонов " + seasons.size() + " (" + seasonal + " квестов), сюжетных цепочек " + chains.size()
                + " (" + story + " шагов).");
    }

    /** forcePremium — весь список только для Ферма+ (премиум-пулы и премиум-цепочки). */
    private void readPool(ConfigurationSection sec, Category cat, List<Quest> out, boolean forcePremium) {
        if (sec == null) return;
        for (String id : sec.getKeys(false)) {
            ConfigurationSection q = sec.getConfigurationSection(id);
            if (q == null) continue;
            ObjectiveType type = ObjectiveType.parse(q.getString("objective.type"));
            if (type == null) {
                plugin.getLogger().warning("quests.yml: у квеста '" + id + "' неизвестный objective.type '"
                        + q.getString("objective.type") + "' — пропуск");
                continue;
            }
            Quest quest = new Quest(id, cat, q.getString("name", id), q.getStringList("description"),
                    material(q.getString("icon"), Material.PAPER), type,
                    q.getStringList("objective.targets"), Math.max(1, q.getInt("objective.amount", 1)),
                    q.getStringList("rewards.lines"), q.getStringList("rewards.commands"),
                    forcePremium || q.getBoolean("premium", false),
                    q.getStringList("premium-rewards.lines"), q.getStringList("premium-rewards.commands"));
            out.add(quest);
            if (cat != Category.SEASONAL && cat != Category.STORY && byKey.containsKey(cat.key + ":" + id))
                plugin.getLogger().warning("quests.yml: id '" + id + "' повторяется в " + cat.key
                        + " (обычные и премиум-квесты должны называться по-разному)");
            byKey.putIfAbsent(cat.key + ":" + id, quest);
        }
    }

    /** YAML сам превращает 2026-12-01 без кавычек в Date — принимаем и так, и строкой. */
    private LocalDate date(Object v, String seasonId) {
        if (v instanceof java.util.Date d) return d.toInstant().atZone(java.time.ZoneOffset.UTC).toLocalDate();
        if (v instanceof LocalDate d) return d;
        String s = v == null ? null : v.toString().trim();
        try { return LocalDate.parse(s); }
        catch (DateTimeParseException | NullPointerException e) {
            plugin.getLogger().warning("quests.yml: сезон '" + seasonId + "' — дата должна быть вида 2026-12-01, сейчас: " + s);
            return null;
        }
    }

    private Material material(String name, Material def) {
        if (name == null) return def;
        Material m = Material.matchMaterial(name.trim());
        return m == null ? def : m;
    }

    public int dailyCount() { return dailyCount; }
    public int weeklyCount() { return weeklyCount; }
    public List<Quest> dailyPool() { return dailyPool; }
    public List<Quest> weeklyPool() { return weeklyPool; }
    public int dailyPremiumCount() { return dailyPremiumCount; }
    public int weeklyPremiumCount() { return weeklyPremiumCount; }
    public List<Quest> dailyPremiumPool() { return dailyPremiumPool; }
    public List<Quest> weeklyPremiumPool() { return weeklyPremiumPool; }
    public Map<String, Chain> chains() { return chains; }

    /** Сезон, который идёт сегодня (первый подходящий), или null. */
    public Season activeSeason(LocalDate today) {
        for (Season s : seasons) if (s.active(today)) return s;
        return null;
    }

    public Quest find(Category cat, String id) { return byKey.get(cat.key + ":" + id); }
}
