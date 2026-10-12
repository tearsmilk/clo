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
    public String bestFish = null;
    public double bestWeight = 0;
    public final Map<String, Integer> count = new HashMap<>();
    public final Map<String, Double> best = new HashMap<>();
    public boolean dirty = false;

    public int known() { return count.size(); }

    /** @return true, если это новый личный рекорд по виду */
    public boolean record(Fish f, double weight) {
        caught++;
        count.merge(f.id(), 1, Integer::sum);
        boolean rec = weight > best.getOrDefault(f.id(), 0.0);
        if (rec) best.put(f.id(), weight);
        if (weight > bestWeight) { bestWeight = weight; bestFish = f.id(); }
        dirty = true;
        return rec;
    }

    public static PlayerStats load(File file) {
        PlayerStats d = new PlayerStats();
        if (!file.exists()) return d;
        YamlConfiguration y = YamlConfiguration.loadConfiguration(file);
        d.name = y.getString("name", "");
        d.caught = y.getInt("caught", 0);
        d.earned = y.getDouble("earned", 0);
        d.bestFish = y.getString("best.fish", null);
        d.bestWeight = y.getDouble("best.weight", 0);
        ConfigurationSection c = y.getConfigurationSection("count");
        if (c != null) for (String k : c.getKeys(false)) d.count.put(k, c.getInt(k));
        ConfigurationSection b = y.getConfigurationSection("records");
        if (b != null) for (String k : b.getKeys(false)) d.best.put(k, b.getDouble(k));
        return d;
    }

    public void save(File file) throws IOException {
        YamlConfiguration y = new YamlConfiguration();
        y.set("name", name);
        y.set("caught", caught);
        y.set("earned", earned);
        y.set("best.fish", bestFish);
        y.set("best.weight", bestWeight);
        for (Map.Entry<String, Integer> e : count.entrySet()) y.set("count." + e.getKey(), e.getValue());
        for (Map.Entry<String, Double> e : best.entrySet()) y.set("records." + e.getKey(), e.getValue());
        file.getParentFile().mkdirs();
        y.save(file);
        dirty = false;
    }
}
