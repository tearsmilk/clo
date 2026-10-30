package ink.hoka.zenquests;

import ink.hoka.zenquests.model.Category;
import ink.hoka.zenquests.model.ObjectiveType;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Квесты OBTAIN: раз в секунду сравнивает, сколько нужных предметов у игрока в инвентаре, с прошлым замером —
 * прирост засчитывается как прогресс. Так считается мука из мебели-жёрнова, у которой нет события.
 * Замер хранится в прогрессе игрока под ключом «<квест>#seen:<цель>» (не теряется при перезаходе).
 */
public final class ObtainTracker implements Runnable {

    private final ZenQuests plugin;

    public ObtainTracker(ZenQuests plugin) { this.plugin = plugin; }

    @Override
    public void run() {
        QuestManager qm = plugin.quests();
        for (Player p : Bukkit.getOnlinePlayers()) {
            Set<String> targets = new HashSet<>();
            Map<String, QuestManager.Entry> active = new HashMap<>();
            for (Category c : Category.values()) for (QuestManager.Entry e : qm.entries(p, c)) {
                if (e.quest().type() != ObjectiveType.OBTAIN || qm.isDone(p, e) || e.quest().targets().isEmpty()) continue;
                for (String t : e.quest().targets()) { String n = norm(t); targets.add(n); active.put(e.key() + "#seen:" + n, e); }
            }
            if (targets.isEmpty()) continue;
            Map<String, Integer> counts = new HashMap<>();
            for (ItemStack it : p.getInventory().getContents()) {
                if (it == null || it.getType().isAir()) continue;
                String n = norm(itemName(it));
                if (targets.contains(n)) counts.merge(n, it.getAmount(), Integer::sum);
            }
            PlayerData d = qm.data(p);
            Map<String, Integer> credited = new HashMap<>();
            for (Map.Entry<String, QuestManager.Entry> a : active.entrySet()) {
                String seenKey = a.getKey(); String t = seenKey.substring(seenKey.indexOf("#seen:") + 6);
                int now = counts.getOrDefault(t, 0);
                Integer seen = d.progress.get(seenKey);
                if (seen == null) { d.progress.put(seenKey, now); d.dirty = true; continue; }   // первый замер — база
                if (now > seen) credited.merge(t, Math.max(credited.getOrDefault(t, 0), now - seen), Math::max);
                if (now != seen) { d.progress.put(seenKey, now); d.dirty = true; }
            }
            for (Map.Entry<String, Integer> c : credited.entrySet()) qm.progress(p, ObjectiveType.OBTAIN, c.getKey(), c.getValue());
        }
    }

    static String norm(String s) {
        String n = s == null ? "" : s.trim().toLowerCase(Locale.ROOT);
        return n.startsWith("nexo:") ? n.substring(5) : n;
    }

    /** Имя предмета: id Nexo, если есть, иначе материал. */
    static String itemName(ItemStack it) {
        try {
            Class<?> items = Class.forName("com.nexomc.nexo.api.NexoItems");
            Object id = items.getMethod("idFromItem", ItemStack.class).invoke(null, it);
            if (id != null) return id.toString();
        } catch (Throwable ignored) { }
        return it.getType().name();
    }
}
