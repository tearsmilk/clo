package ink.hoka.zenfishing;

import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/** Статистика рыбака: plugins/ZenFishing/players/<uuid>.yml */
public final class PlayerStats {

    public String name = "";
    public int caught = 0;
    public double earned = 0;
    public String bestFish = null;      // самая редкая пойманная
    public int bestRarity = -1;
    public final Map<String, Integer> count = new HashMap<>();
    public boolean journalGiven = false;   // рыбацкий журнал уже выдавался при входе
    public boolean dirty = false;

    public int known() { return count.size(); }

    /** @return true, если этот вид пойман впервые */
    public boolean record(Fish f) {
        caught++;
        boolean first = count.merge(f.id(), 1, Integer::sum) == 1;
        if (f.rarity().order() > bestRarity) { bestRarity = f.rarity().order(); bestFish = f.id(); }
        dirty = true;
        return first;
    }

    public static PlayerStats load(File file) {
        PlayerStats d = new PlayerStats();
        if (!file.exists()) return d;
        YamlConfiguration y = YamlConfiguration.loadConfiguration(file);
        d.name = y.getString("name", "");
        d.caught = y.getInt("caught", 0);
        d.earned = y.getDouble("earned", 0);
        d.bestFish = y.getString("best.fish", null);
        d.bestRarity = y.getInt("best.rarity", -1);
        d.journalGiven = y.getBoolean("journal-given", false);
        ConfigurationSection c = y.getConfigurationSection("count");
        if (c != null) for (String k : c.getKeys(false)) d.count.put(k, c.getInt(k));
        return d;
    }

    public void save(File file) throws IOException {
        YamlConfiguration y = new YamlConfiguration();
        y.set("name", name);
        y.set("caught", caught);
        y.set("earned", earned);
        y.set("best.fish", bestFish);
        y.set("best.rarity", bestRarity);
        y.set("journal-given", journalGiven);
        for (Map.Entry<String, Integer> e : count.entrySet()) y.set("count." + e.getKey(), e.getValue());
        file.getParentFile().mkdirs();
        y.save(file);
        dirty = false;
    }
}
