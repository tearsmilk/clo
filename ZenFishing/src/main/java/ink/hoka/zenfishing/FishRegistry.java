package ink.hoka.zenfishing;

import org.bukkit.Location;
import org.bukkit.block.Biome;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.Set;

/** Рыба и редкости из fish.yml; выбор улова с учётом удачи, подписки и биома. */
public final class FishRegistry {

    private final ZenFishing plugin;
    private final Map<String, Rarity> rarities = new LinkedHashMap<>();
    private final Map<String, Fish> fish = new LinkedHashMap<>();
    private final Random rnd = new Random();

    public FishRegistry(ZenFishing plugin) { this.plugin = plugin; }

    public void load() {
        rarities.clear(); fish.clear();
        YamlConfiguration y = YamlConfiguration.loadConfiguration(new File(plugin.getDataFolder(), "fish.yml"));
        ConfigurationSection rs = y.getConfigurationSection("rarities");
        int order = 0;
        if (rs != null) for (String k : rs.getKeys(false)) {
            ConfigurationSection s = rs.getConfigurationSection(k);
            if (s == null) continue;
            rarities.put(k, new Rarity(k, s.getString("name", k), s.getString("color", "&f"), s.getDouble("weight", 1), s.getInt("xp", 5), order++));
        }
        ConfigurationSection fs = y.getConfigurationSection("fish");
        if (fs != null) for (String k : fs.getKeys(false)) {
            ConfigurationSection s = fs.getConfigurationSection(k);
            if (s == null) continue;
            Rarity r = rarities.get(s.getString("rarity", "common"));
            if (r == null) { plugin.getLogger().warning("fish.yml: у рыбы " + k + " неизвестная редкость " + s.getString("rarity")); continue; }
            List<Double> w = s.getDoubleList("weight");
            double min = w.size() > 0 ? w.get(0) : 0.5, max = w.size() > 1 ? w.get(1) : min;
            Set<String> biomes = new HashSet<>();
            for (String b : s.getStringList("biomes")) biomes.add(b.trim().toUpperCase(Locale.ROOT));
            fish.put(k, new Fish(k, s.getString("name", k), s.getString("item", "COD"), r, min, Math.max(min, max),
                    s.getDouble("price", 5), s.getDouble("price-per-kg", 0), s.getBoolean("premium", false),
                    biomes, s.getStringList("lore"), s.contains("model") ? s.getString("model", "") : null));
        }
    }

    public Map<String, Fish> all() { return Collections.unmodifiableMap(fish); }
    public Fish get(String id) { return id == null ? null : fish.get(id); }
    public Rarity rarity(String id) { return rarities.get(id); }
    public int size() { return fish.size(); }

    /** Все виды, отсортированные по редкости (обычные первыми), внутри — как в файле. */
    public List<Fish> sorted() {
        List<Fish> out = new ArrayList<>(fish.values());
        out.sort((a, b) -> Integer.compare(a.rarity().order(), b.rarity().order()));
        return out;
    }

    /**
     * Выбор улова. Сначала редкость (веса редкостей выше первой умножаются на 1+luck), потом вид среди
     * подходящих по биому и подписке; если на редкости нет кандидатов — спускаемся ниже.
     */
    public Fish roll(Location hook, double luck, boolean premium) {
        if (fish.isEmpty() || rarities.isEmpty()) return null;
        List<Rarity> rs = new ArrayList<>(rarities.values());
        double total = 0;
        double[] w = new double[rs.size()];
        for (int i = 0; i < rs.size(); i++) { w[i] = rs.get(i).weight() * (i == 0 ? 1 : 1 + Math.max(0, luck)); total += w[i]; }
        double x = rnd.nextDouble() * total;
        int pick = 0;
        for (int i = 0; i < w.length; i++) { x -= w[i]; if (x <= 0) { pick = i; break; } }
        Set<String> groups = biomeGroups(hook);
        for (int i = pick; i >= 0; i--) {
            List<Fish> c = new ArrayList<>();
            for (Fish f : fish.values()) {
                if (f.rarity() != rs.get(i)) continue;
                if (f.premium() && !premium) continue;
                if (!f.biomes().isEmpty() && Collections.disjoint(f.biomes(), groups)) continue;
                c.add(f);
            }
            if (!c.isEmpty()) return c.get(rnd.nextInt(c.size()));
        }
        return null;
    }

    /** Случайный вес: равномерно в [min,max], big сдвигает к максимуму (0..1). */
    public double rollWeight(Fish f, double big) {
        double t = rnd.nextDouble();
        t = Math.pow(t, 1.0 / (1.0 + Math.max(0, big) * 3));   // big=0.3 → заметно крупнее в среднем
        double v = f.minWeight() + (f.maxWeight() - f.minWeight()) * t;
        return Math.round(v * 100.0) / 100.0;
    }

    /** Группы биома крючка + его полный ключ (minecraft:river) и имя (RIVER). */
    static Set<String> biomeGroups(Location l) {
        Set<String> g = new HashSet<>();
        if (l == null || l.getWorld() == null) return g;
        Biome b = l.getBlock().getBiome();
        String key = b.getKey().toString(), name = b.getKey().getKey().toUpperCase(Locale.ROOT);
        g.add(key.toUpperCase(Locale.ROOT)); g.add(name);
        if (name.contains("OCEAN") || name.contains("BEACH")) g.add("OCEAN");
        if (name.contains("RIVER")) g.add("RIVER");
        if (name.contains("SWAMP") || name.contains("MANGROVE")) g.add("SWAMP");
        if (name.contains("LUSH") || name.contains("CHERRY") || name.contains("MEADOW")) g.add("LUSH");
        if (name.contains("FROZEN") || name.contains("SNOWY") || name.contains("ICE") || name.contains("COLD") || name.contains("TAIGA")) g.add("COLD");
        if (name.contains("JUNGLE") || name.contains("BAMBOO")) g.add("JUNGLE");
        // реки/озёра на равнинах, в лесах и т.п. считаем «речными», чтобы речная рыба ловилась в любом пруду
        if (!g.contains("OCEAN")) g.add("RIVER");
        return g;
    }
}
