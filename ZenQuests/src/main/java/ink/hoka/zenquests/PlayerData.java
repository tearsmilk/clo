package ink.hoka.zenquests;

import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Прогресс одного игрока. Ключи прогресса:
 *   daily:<id>, weekly:<id>, seasonal:<seasonId>:<id>, story:<chain>:<step>
 * Хранится в plugins/ZenQuests/players/<uuid>.yml
 */
public final class PlayerData {

    public String dailyPeriod = "";            // дата, на которую выданы ежедневные
    public List<String> daily = new ArrayList<>();
    public List<String> dailyPremium = new ArrayList<>();   // выдаются всем, видны только с Ферма+
    public String weeklyPeriod = "";           // неделя, на которую выданы еженедельные
    public List<String> weekly = new ArrayList<>();
    public List<String> weeklyPremium = new ArrayList<>();
    public final Map<String, Integer> progress = new HashMap<>();
    public final Set<String> claimed = new HashSet<>();
    public final Map<String, Integer> storyStep = new HashMap<>();   // цепочка → номер текущего шага
    public final List<String> pinned = new ArrayList<>();            // ключи квестов, закреплённых в худе (по порядку)
    public boolean pinnedInit = false;                                 // ежедневные уже закреплялись автоматически
    public boolean storyPinned = true;
    public boolean bookGiven = false;                                  // книга квестов уже выдавалась                                 // текущий сюжетный квест показывать в худе
    public boolean dirty = false;

    public int get(String key) { return progress.getOrDefault(key, 0); }

    /** Убрать прогресс и награды с заданным префиксом (при сбросе дня/недели/сезона). */
    public void clearPrefix(String prefix) {
        progress.keySet().removeIf(k -> k.startsWith(prefix));
        claimed.removeIf(k -> k.startsWith(prefix));
        pinned.removeIf(k -> k.startsWith(prefix));
        dirty = true;
    }

    public static PlayerData load(File file) {
        PlayerData d = new PlayerData();
        if (!file.exists()) return d;
        YamlConfiguration y = YamlConfiguration.loadConfiguration(file);
        d.dailyPeriod = y.getString("daily.period", "");
        d.daily = new ArrayList<>(y.getStringList("daily.quests"));
        d.dailyPremium = new ArrayList<>(y.getStringList("daily.premium"));
        d.weeklyPeriod = y.getString("weekly.period", "");
        d.weekly = new ArrayList<>(y.getStringList("weekly.quests"));
        d.weeklyPremium = new ArrayList<>(y.getStringList("weekly.premium"));
        // ключи прогресса содержат «:», а в YAML-путях точка — поэтому храним списком «ключ=число»
        for (String line : y.getStringList("progress")) {
            int i = line.lastIndexOf('=');
            if (i <= 0) continue;
            try { d.progress.put(line.substring(0, i), Integer.parseInt(line.substring(i + 1))); }
            catch (NumberFormatException ignored) { }
        }
        d.claimed.addAll(y.getStringList("claimed"));
        d.pinned.addAll(y.getStringList("pinned"));
        d.pinnedInit = y.getBoolean("pinned-init", false);
        d.storyPinned = y.getBoolean("story-pinned", true);
        d.bookGiven = y.getBoolean("book-given", false);
        ConfigurationSection st = y.getConfigurationSection("story");
        if (st != null) for (String chain : st.getKeys(false)) d.storyStep.put(chain, st.getInt(chain, 0));
        return d;
    }

    public void save(File file) throws IOException {
        YamlConfiguration y = new YamlConfiguration();
        y.set("daily.period", dailyPeriod);
        y.set("daily.quests", daily);
        y.set("daily.premium", dailyPremium);
        y.set("weekly.period", weeklyPeriod);
        y.set("weekly.quests", weekly);
        y.set("weekly.premium", weeklyPremium);
        List<String> pr = new ArrayList<>();
        for (Map.Entry<String, Integer> e : progress.entrySet()) pr.add(e.getKey() + "=" + e.getValue());
        y.set("progress", pr);
        y.set("claimed", new ArrayList<>(claimed));
        y.set("pinned", new ArrayList<>(pinned));
        y.set("pinned-init", pinnedInit);
        y.set("story-pinned", storyPinned);
        y.set("book-given", bookGiven);
        for (Map.Entry<String, Integer> e : storyStep.entrySet()) y.set("story." + e.getKey(), e.getValue());
        file.getParentFile().mkdirs();
        y.save(file);
        dirty = false;
    }
}
