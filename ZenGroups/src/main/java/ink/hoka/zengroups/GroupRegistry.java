package ink.hoka.zengroups;

import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** groups.yml + permissions.yml. */
public final class GroupRegistry {

    private final ZenGroups plugin;
    private final Map<String, Group> groups = new LinkedHashMap<>();

    public GroupRegistry(ZenGroups plugin) { this.plugin = plugin; }

    public void load() {
        groups.clear();
        YamlConfiguration g = YamlConfiguration.loadConfiguration(new File(plugin.getDataFolder(), "groups.yml"));
        YamlConfiguration p = YamlConfiguration.loadConfiguration(new File(plugin.getDataFolder(), "permissions.yml"));
        for (String id : g.getKeys(false)) {
            ConfigurationSection s = g.getConfigurationSection(id);
            if (s == null) continue;
            String k = id.toLowerCase(Locale.ROOT);
            groups.put(k, new Group(k, s.getString("display", id), s.getInt("weight", 0),
                    s.getString("tab-prefix", ""), s.getString("tab-suffix", ""), s.getString("chat-prefix", ""), s.getString("chat-suffix", ""),
                    s.getString("name-prefix", ""), s.getString("name-suffix", ""),
                    lower(s.getStringList("inherits")), p.getStringList(id)));
        }
        String def = plugin.defaultGroup();
        if (!groups.containsKey(def)) {
            plugin.getLogger().warning("groups.yml: нет группы по умолчанию '" + def + "' — создана пустая.");
            groups.put(def, new Group(def, def, 0, "", "", "", "", "", "", List.of(), p.getStringList(def)));
        }
    }

    private static List<String> lower(List<String> in) { List<String> o = new ArrayList<>(); for (String s : in) o.add(s.toLowerCase(Locale.ROOT)); return o; }

    public Group get(String id) { return id == null ? null : groups.get(id.toLowerCase(Locale.ROOT)); }
    public Map<String, Group> all() { return Collections.unmodifiableMap(groups); }
    public int size() { return groups.size(); }

    /** Права группы с наследованием: «-право» снимает ранее добавленное. Порядок — родители, потом своё. */
    public Map<String, Boolean> effectivePerms(Group g) {
        Map<String, Boolean> out = new LinkedHashMap<>();
        collect(g, out, new HashSet<>());
        return out;
    }

    private void collect(Group g, Map<String, Boolean> out, Set<String> seen) {
        if (g == null || !seen.add(g.id())) return;
        for (String parent : g.inherits()) collect(get(parent), out, seen);
        for (String perm : g.perms()) {
            String s = perm.trim();
            if (s.isEmpty()) continue;
            if (s.startsWith("-")) out.put(s.substring(1).toLowerCase(Locale.ROOT), false);
            else out.put(s.toLowerCase(Locale.ROOT), true);
        }
    }

    /** Суммарные права нескольких групп: от младшей (меньший вес) к старшей, старшая перекрывает. */
    public Map<String, Boolean> effectivePerms(List<Group> gs) {
        List<Group> sorted = new ArrayList<>(gs);
        sorted.sort((a, b) -> Integer.compare(a.weight(), b.weight()));
        Map<String, Boolean> out = new LinkedHashMap<>();
        Set<String> seen = new LinkedHashSet<>();
        for (Group g : sorted) { seen.clear(); collect(g, out, seen); }
        return out;
    }
}
